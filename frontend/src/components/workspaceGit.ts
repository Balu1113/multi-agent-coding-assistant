import git from 'isomorphic-git'
import http from 'isomorphic-git/http/web'

interface GitFileHandle {
  kind: 'file'
  name: string
  getFile(): Promise<File>
  createWritable(): Promise<{
    write(data: string | Uint8Array): Promise<void>
    close(): Promise<void>
  }>
}

interface GitDirectoryHandle {
  kind: 'directory'
  name: string
  values(): AsyncIterable<GitEntryHandle>
  getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<GitDirectoryHandle>
  getFileHandle(name: string, options?: { create?: boolean }): Promise<GitFileHandle>
  removeEntry(name: string, options?: { recursive?: boolean }): Promise<void>
}

type GitEntryHandle = GitFileHandle | GitDirectoryHandle

export interface GitChange {
  path: string
  status: 'Added' | 'Modified' | 'Deleted' | 'Staged'
}

function fsError(code: string, message: string): Error & { code: string } {
  return Object.assign(new Error(message), { code })
}

function pathParts(path: string): string[] {
  const parts = path.replace(/\\/g, '/').split('/').filter((part) => part && part !== '.')
  if (parts.some((part) => part === '..')) throw fsError('EINVAL', 'Path escapes the workspace.')
  return parts
}

async function getDirectory(root: GitDirectoryHandle, parts: string[], create = false): Promise<GitDirectoryHandle> {
  let directory = root
  for (const part of parts) {
    try {
      directory = await directory.getDirectoryHandle(part, { create })
    } catch (error) {
      if ((error as DOMException).name === 'NotFoundError') throw fsError('ENOENT', `Directory not found: ${part}`)
      if ((error as DOMException).name === 'TypeMismatchError') throw fsError('ENOTDIR', `Not a directory: ${part}`)
      throw error
    }
  }
  return directory
}

async function getEntry(root: GitDirectoryHandle, parts: string[]): Promise<GitEntryHandle> {
  if (parts.length === 0) return root
  const parent = await getDirectory(root, parts.slice(0, -1))
  const name = parts[parts.length - 1]
  try {
    return await parent.getDirectoryHandle(name)
  } catch (error) {
    if ((error as DOMException).name === 'NotFoundError') {
      try {
        return await parent.getFileHandle(name)
      } catch (fileError) {
        if ((fileError as DOMException).name === 'NotFoundError') throw fsError('ENOENT', `File not found: ${name}`)
        if ((fileError as DOMException).name === 'TypeMismatchError') throw fsError('EISDIR', `Is a directory: ${name}`)
        throw fileError
      }
    }
    if ((error as DOMException).name === 'TypeMismatchError') {
      try {
        return await parent.getFileHandle(name)
      } catch {
        throw fsError('ENOENT', `Entry not found: ${name}`)
      }
    }
    throw error
  }
}

function fileStat(file: File) {
  return {
    size: file.size,
    mode: 0o100644,
    mtimeMs: file.lastModified,
    ctimeMs: file.lastModified,
    isFile: () => true,
    isDirectory: () => false,
    isSymbolicLink: () => false,
  }
}

function directoryStat() {
  return {
    size: 0,
    mode: 0o040000,
    mtimeMs: 0,
    ctimeMs: 0,
    isFile: () => false,
    isDirectory: () => true,
    isSymbolicLink: () => false,
  }
}

export function createWorkspaceGitClient(rootHandle: GitDirectoryHandle) {
  const promises = {
    async readFile(path: string, options?: string | { encoding?: string }) {
      const entry = await getEntry(rootHandle, pathParts(path))
      if (entry.kind !== 'file') throw fsError('EISDIR', `Is a directory: ${path}`)
      const file = await entry.getFile()
      const bytes = new Uint8Array(await file.arrayBuffer())
      const encoding = typeof options === 'string' ? options : options?.encoding
      return encoding ? new TextDecoder().decode(bytes) : bytes
    },
    async writeFile(path: string, data: string | Uint8Array) {
      const parts = pathParts(path)
      if (parts.length === 0) throw fsError('EISDIR', 'Cannot write to the workspace directory.')
      const parent = await getDirectory(rootHandle, parts.slice(0, -1), true)
      const handle = await parent.getFileHandle(parts[parts.length - 1], { create: true })
      const writable = await handle.createWritable()
      await writable.write(data)
      await writable.close()
    },
    async readdir(path: string) {
      const directory = await getDirectory(rootHandle, pathParts(path))
      const names: string[] = []
      for await (const entry of directory.values()) names.push(entry.name)
      return names
    },
    async mkdir(path: string) {
      await getDirectory(rootHandle, pathParts(path), true)
    },
    async unlink(path: string) {
      const parts = pathParts(path)
      if (parts.length === 0) throw fsError('EISDIR', 'Cannot remove the workspace directory.')
      const parent = await getDirectory(rootHandle, parts.slice(0, -1))
      try {
        await parent.removeEntry(parts[parts.length - 1])
      } catch (error) {
        if ((error as DOMException).name === 'NotFoundError') throw fsError('ENOENT', `File not found: ${path}`)
        throw error
      }
    },
    async rmdir(path: string) {
      const parts = pathParts(path)
      if (parts.length === 0) return
      const parent = await getDirectory(rootHandle, parts.slice(0, -1))
      try {
        await parent.removeEntry(parts[parts.length - 1], { recursive: true })
      } catch (error) {
        if ((error as DOMException).name === 'NotFoundError') throw fsError('ENOENT', `Directory not found: ${path}`)
        throw error
      }
    },
    async stat(path: string) {
      const entry = await getEntry(rootHandle, pathParts(path))
      return entry.kind === 'directory' ? directoryStat() : fileStat(await entry.getFile())
    },
    async lstat(path: string) {
      return this.stat(path)
    },
    async readlink(path: string) {
      throw fsError('EINVAL', `Symbolic links are not supported in browser workspaces: ${path}`)
    },
    async symlink(_target: string, path: string) {
      throw fsError('ENOSYS', `Symbolic links are not supported in browser workspaces: ${path}`)
    },
  }

  const fs = { promises }
  const dir = '/'

  return {
    async isRepository(): Promise<boolean> {
      try {
        await rootHandle.getDirectoryHandle('.git')
        return true
      } catch {
        return false
      }
    },
    async initialize(): Promise<void> {
      await git.init({ fs, dir })
    },
    async clone(url: string): Promise<void> {
      await git.clone({
        fs,
        http,
        dir,
        url,
        corsProxy: 'http://localhost:8000/api/git-proxy',
        singleBranch: true,
        depth: 1,
        nonBlocking: true,
      })
    },
    async status(): Promise<GitChange[]> {
      const matrix = await git.statusMatrix({ fs, dir })
      return matrix.flatMap(([path, head, workdir, stage]) => {
        if (head === workdir && head === stage) return []
        const status: GitChange['status'] = head === 0
          ? 'Added'
          : workdir === 0
            ? 'Deleted'
            : workdir !== head
              ? 'Modified'
              : 'Staged'
        return [{ path, status }]
      })
    },
    async commit(message: string, authorName: string, authorEmail: string): Promise<string> {
      const matrix = await git.statusMatrix({ fs, dir })
      const changed = matrix.filter(([, head, workdir, stage]) => head !== workdir || head !== stage)
      for (const [path, , workdir, stage] of changed) {
        if (workdir === 0) {
          if (stage !== 0) await git.remove({ fs, dir, filepath: path })
        } else {
          await git.add({ fs, dir, filepath: path })
        }
      }
      return git.commit({ fs, dir, message, author: { name: authorName, email: authorEmail } })
    },
  }
}