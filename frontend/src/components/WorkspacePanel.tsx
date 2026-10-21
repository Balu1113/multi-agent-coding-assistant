import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { createWorkspaceGitClient, type GitChange } from './workspaceGit'
import './WorkspacePanel.css'

interface LocalFileHandle {
  kind: 'file'
  name: string
  requestPermission?(descriptor: { mode: 'readwrite' }): Promise<PermissionState>
  getFile(): Promise<File>
  createWritable(): Promise<{
    write(data: string): Promise<void>
    close(): Promise<void>
  }>
}

interface LocalDirectoryHandle {
  kind: 'directory'
  name: string
  values(): AsyncIterable<LocalHandle>
  requestPermission?(descriptor: { mode: 'readwrite' }): Promise<PermissionState>
  getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<LocalDirectoryHandle>
  getFileHandle(name: string, options?: { create?: boolean }): Promise<LocalFileHandle>
  removeEntry(name: string, options?: { recursive?: boolean }): Promise<void>
}

type LocalHandle = LocalFileHandle | LocalDirectoryHandle

interface FileNode {
  path: string
  handle: LocalHandle
}

interface OpenFile extends Omit<FileNode, 'handle'> {
  handle: LocalFileHandle
  value: string
  savedValue: string
  language: string
}

const HIDDEN_DIRECTORIES = new Set([
  '.git', '.venv', 'venv', 'node_modules', '__pycache__', '.next', '.cache', '.ssh',
  '.pytest_cache', '.mypy_cache', '.ruff_cache', 'coverage', 'dist', 'build', 'target',
])
const MAX_FILE_BYTES = 2 * 1024 * 1024
  const MAX_SCAN_CONTEXT_CHARS = 12_000_000
  const MAX_AGENT_CONTEXT_CHARS = 60_000
  const MAX_AGENT_CONTEXT_FILES = 14
  const MAX_FILE_INVENTORY_CHARS = 8_000
const API_BASE = 'http://localhost:8000'
const GENERATED_LOCKFILES = new Set([
  'bun.lock', 'bun.lockb', 'cargo.lock', 'composer.lock', 'gemfile.lock',
  'go.sum', 'package-lock.json', 'pipfile.lock', 'poetry.lock', 'pnpm-lock.yaml',
  'uv.lock', 'yarn.lock',
])
const MAX_WORKSPACE_HISTORY = 20
const MAX_WORKSPACE_HISTORY_MESSAGE_CHARS = 4000

interface WorkspaceAgentResult {
  type: 'chat' | 'plan' | 'review' | 'coding'
  message?: string
  analysis?: string
  requirement?: string
  plan?: string
  requestPrompt?: string
  changedPaths?: string[]
  toolResults?: WorkspaceToolResult[]
  inspectedFiles?: WorkspaceContextFile[]
}

interface WorkspaceChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface WorkspaceFileChange {
  path: string
  action: 'write' | 'delete' | 'delete_directory'
  content: string
}

interface WorkspaceToolResult {
  tool: 'search_workspace' | 'read_file' | 'list_directory'
  query?: string
  path?: string
  result: string
}

interface WorkspaceToolCall {
  tool: 'search_workspace' | 'read_file' | 'list_directory'
  query?: string
  path?: string
}

interface WorkspaceAgentRetry {
  prompt: string
  approvedRequirement: string
  approvedPlan: string
  toolResults: WorkspaceToolResult[]
  inspectedFiles: WorkspaceContextFile[]
}

interface PendingWorkspaceChanges {
  changes: WorkspaceFileChange[]
  analyzedFiles: Map<string, string>
  analyzedDirectories: Set<string>
  analysis: string
  plan: string
  requirement: string
}

interface WorkspaceContextFile {
  path: string
  content: string
  truncated?: boolean
}

interface WorkspaceContextScan {
  files: WorkspaceContextFile[]
  directories: string[]
  skippedFiles: number
  tooLargePath: string | null
}

interface SelectedWorkspaceContext {
  files: WorkspaceContextFile[]
  inventory: string
}

interface ModelOption {
  id: string
  name: string
  group?: string
}

const FALLBACK_MODELS: ModelOption[] = [
  { id: 'gemini-3.1-flash-lite', name: 'Gemini 3.1 Flash Lite', group: 'General' },
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', group: 'General' },
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', group: 'General' },
  { id: 'groq/llama-3.1-8b-instant', name: 'Groq Llama 3.1 8B', group: 'General' },
  { id: 'groq/llama-3.3-70b-versatile', name: 'Groq Llama 3.3 70B', group: 'General' },
  { id: 'hf/meta-llama/Llama-3.1-8B-Instruct', name: 'HF Llama 3.1 8B', group: 'General' },
]

function editorLanguage(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() || ''
  const languages: Record<string, string> = {
    c: 'c', cpp: 'cpp', cs: 'csharp', css: 'css', go: 'go', h: 'cpp', hpp: 'cpp',
    html: 'html', java: 'java', js: 'javascript', json: 'json', jsx: 'javascript',
    md: 'markdown', php: 'php', py: 'python', rb: 'ruby', rs: 'rust', scss: 'scss',
    sh: 'shell', sql: 'sql', ts: 'typescript', tsx: 'typescript', txt: 'plaintext',
    xml: 'xml', yaml: 'yaml', yml: 'yaml',
  }
  return languages[extension] || 'plaintext'
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The operation could not be completed.'
}

function isContextFile(path: string): boolean {
  const name = path.split('/').pop()?.toLowerCase() || ''
  if (GENERATED_LOCKFILES.has(name)) return false
  if (
    name.startsWith('.env') ||
    /(^|[._-])(secret|credentials?|tokens?|private[_-]?key|id_rsa|id_ed25519)([._-]|$)/i.test(name) ||
    /\.(?:key|pem|p12|pfx|jks)$/i.test(name)
  ) return false
  return true
}

function selectWorkspaceContext(
  files: WorkspaceContextFile[],
  prompt: string,
  activePath: string,
  priorityPaths: string[] = [],
): SelectedWorkspaceContext {
  const stopWords = new Set(['about', 'after', 'could', 'does', 'from', 'have', 'into', 'just', 'make', 'that', 'them', 'then', 'there', 'this', 'what', 'when', 'where', 'which', 'with', 'would', 'your'])
  const terms = [...new Set((prompt.toLowerCase().match(/[a-z0-9_]{3,}/g) || []).filter((term) => !stopWords.has(term)))]
  const ranked = files.map((file, index) => {
    const path = file.path.toLowerCase()
    const content = file.content.toLowerCase()
    let score = priorityPaths.includes(file.path) ? 1000 : file.path === activePath ? 100 : 0
    if (/(^|\/)(readme[^/]*|pyproject\.toml|package\.json|requirements[^/]*|architecture\.md)$/i.test(file.path)) score += 4
    for (const term of terms) {
      if (path.includes(term)) score += 12
      let matches = 0
      let offset = 0
      while (matches < 8) {
        const found = content.indexOf(term, offset)
        if (found < 0) break
        matches += 1
        offset = found + term.length
      }
      score += matches * 2
    }
    return { file, index, score }
  }).sort((left, right) => right.score - left.score || left.index - right.index)

  const inventory = files.map((file) => file.path).join('\n').slice(0, MAX_FILE_INVENTORY_CHARS)
  let remaining = MAX_AGENT_CONTEXT_CHARS - inventory.length - 100
  const selected: WorkspaceContextFile[] = []
  for (const { file } of ranked) {
    if (selected.length >= MAX_AGENT_CONTEXT_FILES || remaining <= 0) break
    const headerLength = file.path.length + 8
    const contentLength = Math.max(0, remaining - headerLength)
    if (contentLength === 0) break
    const content = file.content.slice(0, contentLength)
    const truncated = content.length < file.content.length
    selected.push({ path: file.path, content, truncated })
    remaining -= headerLength + content.length + (truncated ? 30 : 0)
  }
  return { files: selected, inventory }
}

function pathsMentionedIn(text: string, files: WorkspaceContextFile[]): string[] {
  const normalizedText = text.replace(/\\/g, '/').toLowerCase()
  return files
    .map((file) => file.path)
    .filter((path) => normalizedText.includes(path.toLowerCase()))
}

function executeWorkspaceTool(
  toolCall: WorkspaceToolCall,
  files: WorkspaceContextFile[],
  directories: string[],
): WorkspaceToolResult {
  if (toolCall.tool === 'read_file') {
    const path = (toolCall.path || '').replace(/\\/g, '/')
    const file = files.find((candidate) => candidate.path === path)
    if (!file) return { tool: 'read_file', path, result: `File is unavailable for inspection: ${path}` }
    const truncated = file.content.length > 20000
    return {
      tool: 'read_file',
      path,
      result: `File: ${path}\n${file.content.slice(0, 20000)}${truncated ? '\n[File output limited to 20,000 characters]' : ''}`,
    }
  }

  if (toolCall.tool === 'list_directory') {
    const path = (toolCall.path || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
    if (path && !directories.includes(path)) {
      return { tool: 'list_directory', path, result: `Directory does not exist in the scanned workspace: ${path}` }
    }
    const prefix = path ? `${path}/` : ''
    const entries = [
      ...directories.filter((directory) => directory.startsWith(prefix) && directory !== path).map((directory) => directory.slice(prefix.length) + '/'),
      ...files.filter((file) => file.path.startsWith(prefix)).map((file) => file.path.slice(prefix.length)),
    ].filter((entry) => entry && !entry.includes('/'))
    return {
      tool: 'list_directory',
      path,
      result: entries.length ? `Directory: ${path || '/'}\n${[...new Set(entries)].sort().join('\n')}` : `Directory is empty: ${path || '/'}`,
    }
  }

  const query = (toolCall.query || '').trim()
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!terms.length) return { tool: 'search_workspace', query, result: 'Search query is empty.' }
  const matches = files.map((file) => {
    const path = file.path.toLowerCase()
    const content = file.content.toLowerCase()
    const score = terms.reduce((total, term) => total + (path.includes(term) ? 8 : 0) + Math.min(4, content.split(term).length - 1), 0)
    return { file, score }
  }).filter(({ score }) => score > 0).sort((left, right) => right.score - left.score).slice(0, 8)
  if (!matches.length) return { tool: 'search_workspace', query, result: `No files matched: ${query}` }
  const result = matches.map(({ file }) => {
    const lower = file.content.toLowerCase()
    const matchIndex = terms.map((term) => lower.indexOf(term)).filter((index) => index >= 0).sort((a, b) => a - b)[0]
    const start = matchIndex === undefined ? 0 : Math.max(0, matchIndex - 240)
    const excerpt = file.content.slice(start, start + 700)
    return `--- ${file.path} ---\n${excerpt}`
  }).join('\n\n')
  return { tool: 'search_workspace', query, result }
}

function filePathParts(path: string): string[] {
  const normalized = path.replace(/\\/g, '/')
  const parts = normalized.split('/')
  if (
    !normalized || normalized.startsWith('/') || /^[a-z]:/i.test(normalized) ||
    normalized.includes(':') ||
    parts.some((part) => !part || part === '.' || part === '..') ||
    parts.some((part) => part.toLowerCase() === '.git') ||
    /(^|\/)(?:\.env[^/]*|bun\.lockb?|cargo\.lock|composer\.lock|gemfile\.lock|go\.sum|package-lock\.json|pipfile\.lock|poetry\.lock|pnpm-lock\.yaml|uv\.lock|yarn\.lock)$/i.test(normalized) ||
    /(^|[._-])(secret|credentials?|tokens?|private[_-]?key|id_rsa|id_ed25519)([._-]|$)/i.test(parts[parts.length - 1]) ||
    /\.(?:key|pem|p12|pfx|jks)$/i.test(parts[parts.length - 1])
  ) throw new Error(`The agent returned an unsafe file path: ${path}`)
  return parts
}

async function directoryForPath(
  root: LocalDirectoryHandle,
  parts: string[],
  create = true,
): Promise<LocalDirectoryHandle> {
  let directory = root
  for (const part of parts) directory = await directory.getDirectoryHandle(part, create ? { create: true } : undefined)
  return directory
}

async function writeWorkspaceChanges(
  root: LocalDirectoryHandle,
  changes: WorkspaceFileChange[],
  analyzedFiles: Map<string, string>,
  analyzedDirectories: Set<string>,
  openedFiles: Record<string, OpenFile>,
  setOpenedFiles: React.Dispatch<React.SetStateAction<Record<string, OpenFile>>>,
  refreshTree: () => Promise<void>,
): Promise<void> {
  if (!changes.length || changes.length > 20) throw new Error('The agent returned an invalid number of file changes.')
  const seen = new Set<string>()
  let totalChars = 0
  const prepared: Array<{
    path: string
    parts: string[]
    parent: LocalDirectoryHandle
    handle: LocalFileHandle | null
    directoryHandle: LocalDirectoryHandle | null
    original: string | null
    content: string
    action: WorkspaceFileChange['action']
  }> = []

  for (const change of changes) {
    const parts = filePathParts(change.path)
    const path = parts.join('/')
    if (seen.has(path)) throw new Error(`The agent returned a duplicate file change: ${path}`)
    if (!['write', 'delete', 'delete_directory'].includes(change.action) || typeof change.content !== 'string' || change.content.includes('\0')) {
      throw new Error(`The agent returned invalid text for ${path}.`)
    }
    seen.add(path)
    if (change.action === 'write') totalChars += change.content.length
    if (totalChars > 2_000_000) throw new Error('The agent changes exceed the 2 MB workspace limit.')

    if (change.action === 'delete_directory') {
      if (change.content || !analyzedDirectories.has(path)) throw new Error(`The agent tried to remove a directory that was not included in project analysis: ${path}`)
      const parent = await directoryForPath(root, parts.slice(0, -1), false)
      const directoryHandle = await parent.getDirectoryHandle(parts[parts.length - 1])
      const requestedChanges = new Map(changes.map((candidate) => [candidate.path.replace(/\\/g, '/'), candidate]))
      const verifyChildren = async (directory: LocalDirectoryHandle, directoryPath: string): Promise<void> => {
        for await (const child of directory.values()) {
          const childPath = `${directoryPath}/${child.name}`
          const childChange = requestedChanges.get(childPath)
          if (child.kind === 'directory') {
            if (childChange?.action !== 'delete_directory') throw new Error(`Cannot remove ${path}: include the nested directory ${childPath} in the reviewed changes.`)
            await verifyChildren(child, childPath)
          } else if (childChange?.action !== 'delete') {
            throw new Error(`Cannot remove ${path}: include the child file ${childPath} in the reviewed changes.`)
          }
        }
      }
      await verifyChildren(directoryHandle, path)
      prepared.push({
        path,
        parts,
        parent,
        handle: null,
        directoryHandle,
        original: null,
        content: '',
        action: change.action,
      })
      continue
    }

    const parent = await directoryForPath(root, parts.slice(0, -1), change.action !== 'delete')
    let handle: LocalFileHandle | null = null
    let original: string | null = null
    try {
      handle = await parent.getFileHandle(parts[parts.length - 1])
    } catch (error) {
      if (!(error instanceof DOMException) || error.name !== 'NotFoundError') throw error
    }
    if (handle) {
      const analyzedContent = analyzedFiles.get(path)
      if (analyzedContent === undefined) throw new Error(`The agent tried to change a file that was not included in project analysis: ${path}`)
      const file = await handle.getFile()
      if (file.size > MAX_FILE_BYTES) throw new Error(`${path} exceeds the 2 MB file limit.`)
      original = await file.text()
      if (original.includes('\0')) throw new Error(`${path} is binary and cannot be rewritten as text.`)
      if (original !== analyzedContent) throw new Error(`${path} changed after analysis. Refresh the workspace and retry to avoid overwriting newer work.`)
    }
    if (change.action === 'delete' && !handle) throw new Error(`The agent tried to delete a file that does not exist: ${path}`)
    prepared.push({ path, parts, parent, handle, directoryHandle: null, original, content: change.content, action: change.action })
  }

  const applied: typeof prepared = []
  try {
    const orderedChanges = [...prepared].sort((left, right) => {
      const rank = (action: WorkspaceFileChange['action']) => action === 'write' ? 0 : action === 'delete' ? 1 : 2
      return rank(left.action) - rank(right.action) || (left.action === 'delete_directory' ? right.parts.length - left.parts.length : 0)
    })
    for (const change of orderedChanges) {
      applied.push(change)
      if (change.action === 'delete') {
        await change.parent.removeEntry(change.parts[change.parts.length - 1])
        continue
      }
      if (change.action === 'delete_directory') {
        for await (const _child of (change.directoryHandle as LocalDirectoryHandle).values()) {
          throw new Error(`Directory ${change.path} still contains unreviewed entries and was not removed.`)
        }
        await change.parent.removeEntry(change.parts[change.parts.length - 1])
        continue
      }
      const handle = change.handle || await change.parent.getFileHandle(change.parts[change.parts.length - 1], { create: true })
      const writable = await handle.createWritable()
      await writable.write(change.content)
      await writable.close()
    }
  } catch (error) {
    let rollbackFailed = false
    for (const change of applied.reverse()) {
      try {
        if (change.action === 'delete_directory') {
          await change.parent.getDirectoryHandle(change.parts[change.parts.length - 1], { create: true })
        } else if (change.original === null) {
          await change.parent.removeEntry(change.parts[change.parts.length - 1])
        } else {
          const handle = change.action === 'delete'
            ? await change.parent.getFileHandle(change.parts[change.parts.length - 1], { create: true })
            : change.handle || await change.parent.getFileHandle(change.parts[change.parts.length - 1], { create: true })
          const writable = await handle.createWritable()
          await writable.write(change.original)
          await writable.close()
        }
      } catch {
        rollbackFailed = true
      }
    }
    const detail = errorMessage(error)
    throw new Error(rollbackFailed ? `Could not apply the changes and rollback was incomplete: ${detail}` : `Could not apply the changes; original files were restored: ${detail}`)
  }

  setOpenedFiles((previous) => {
    const next = { ...previous }
    for (const change of prepared) {
      if (change.action === 'delete_directory') {
        for (const path of Object.keys(next)) {
          if (path === change.path || path.startsWith(`${change.path}/`)) delete next[path]
        }
        continue
      }
      if (change.action === 'delete') {
        delete next[change.path]
        continue
      }
      const opened = next[change.path]
      if (opened) next[change.path] = { ...opened, value: change.content, savedValue: change.content }
    }
    return next
  })
  await refreshTree()
}

async function scanWorkspace(
  root: LocalDirectoryHandle,
  openedFiles: Record<string, OpenFile>,
): Promise<WorkspaceContextScan> {
  const files: WorkspaceContextFile[] = []
  const directories: string[] = []
  let usedChars = 0
  let skippedFiles = 0
  let tooLargePath: string | null = null

  const visit = async (directory: LocalDirectoryHandle, parentPath: string): Promise<void> => {
    for await (const handle of directory.values()) {
      if (tooLargePath) return
      const path = parentPath ? `${parentPath}/${handle.name}` : handle.name
      if (handle.kind === 'directory') {
        if (!HIDDEN_DIRECTORIES.has(handle.name.toLowerCase())) {
          directories.push(path)
          await visit(handle, path)
        }
        continue
      }
      if (!isContextFile(path)) {
        skippedFiles += 1
        continue
      }

      try {
        let content = openedFiles[path]?.value
        if (content === undefined) {
          const file = await handle.getFile()
          if (file.size > MAX_FILE_BYTES) {
            const sample = await file.slice(0, 8192).text()
            if (!sample.includes('\0')) {
              tooLargePath = path
              return
            }
            skippedFiles += 1
            continue
          }
          content = await file.text()
        }
        if (content.includes('\0')) {
          skippedFiles += 1
          continue
        }

        const sectionChars = path.length + content.length + 12
        if (usedChars + sectionChars > MAX_SCAN_CONTEXT_CHARS) {
          tooLargePath = path
          return
        }
        files.push({ path, content })
        usedChars += sectionChars
      } catch {
        skippedFiles += 1
      }
    }
  }

  await visit(root, '')
  return { files, directories, skippedFiles, tooLargePath }
}

export default function WorkspacePanel() {
  const [rootHandle, setRootHandle] = useState<LocalDirectoryHandle | null>(null)
  const [childrenByPath, setChildrenByPath] = useState<Record<string, FileNode[]>>({})
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  const [openedFiles, setOpenedFiles] = useState<Record<string, OpenFile>>({})
  const [activePath, setActivePath] = useState('')
  const [status, setStatus] = useState('No folder open')
  const [busy, setBusy] = useState(false)
  const [agentOpen, setAgentOpen] = useState(false)
  const [agentPrompt, setAgentPrompt] = useState('')
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState('')
  const [agentResult, setAgentResult] = useState<WorkspaceAgentResult | null>(null)
  const [workspaceAgentRetry, setWorkspaceAgentRetry] = useState<WorkspaceAgentRetry | null>(null)
  const [conversationHistory, setConversationHistory] = useState<WorkspaceChatMessage[]>([])
  const [pendingWorkspaceChanges, setPendingWorkspaceChanges] = useState<PendingWorkspaceChanges | null>(null)
  const [selectedModel, setSelectedModel] = useState(() =>
    localStorage.getItem('workspace_selected_model') || 'gemini-3.1-flash-lite'
  )
  const [availableModels, setAvailableModels] = useState<ModelOption[]>(FALLBACK_MODELS)
  const [gitOpen, setGitOpen] = useState(false)
  const [gitInitialized, setGitInitialized] = useState(false)
  const [gitChanges, setGitChanges] = useState<GitChange[]>([])
  const [gitBusy, setGitBusy] = useState(false)
  const [gitError, setGitError] = useState('')
  const [cloneUrl, setCloneUrl] = useState('')
  const [commitMessage, setCommitMessage] = useState('')
  const [gitAuthorName, setGitAuthorName] = useState(() => localStorage.getItem('workspace_git_author_name') || '')
  const [gitAuthorEmail, setGitAuthorEmail] = useState(() => localStorage.getItem('workspace_git_author_email') || '')
  const saveCurrentRef = useRef<() => void>(() => {})

  const activeFile = openedFiles[activePath]
  const openPaths = Object.keys(openedFiles)
  const dirtyCount = Object.values(openedFiles).filter((file) => file.value !== file.savedValue).length
  const modelGroups = availableModels.reduce<Record<string, ModelOption[]>>((groups, model) => {
    const group = model.group || 'Models'
    if (!groups[group]) groups[group] = []
    groups[group].push(model)
    return groups
  }, {})

  useEffect(() => {
    let active = true
    fetch(`${API_BASE}/api/models/`)
      .then((response) => response.json())
      .then((data) => {
        if (!active) return
        if (Array.isArray(data.models) && data.models.length > 0) setAvailableModels(data.models)
        const savedModel = localStorage.getItem('workspace_selected_model')
        const validSavedModel = data.models?.some((model: ModelOption) => model.id === savedModel)
        const model = validSavedModel ? savedModel : data.current
        if (typeof model === 'string' && model) setSelectedModel(model)
      })
      .catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!rootHandle || !gitOpen || !gitInitialized) return
    let active = true
    const gitClient = createWorkspaceGitClient(rootHandle)
    const refresh = () => {
      void gitClient.status()
        .then((changes) => { if (active) setGitChanges(changes) })
        .catch((error) => { if (active) setGitError(errorMessage(error)) })
    }
    refresh()
    const interval = window.setInterval(refresh, 5000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [gitInitialized, gitOpen, rootHandle])

  const readChildren = async (directory: LocalDirectoryHandle, parentPath: string) => {
    const children: FileNode[] = []
    for await (const handle of directory.values()) {
      if (handle.kind === 'directory' && HIDDEN_DIRECTORIES.has(handle.name)) continue
      children.push({
        path: parentPath ? `${parentPath}/${handle.name}` : handle.name,
        handle,
      })
    }
    children.sort((left, right) => {
      const leftIsDirectory = left.handle.kind === 'directory'
      const rightIsDirectory = right.handle.kind === 'directory'
      if (leftIsDirectory !== rightIsDirectory) return leftIsDirectory ? -1 : 1
      return left.handle.name.localeCompare(right.handle.name)
    })
    setChildrenByPath((previous) => ({ ...previous, [parentPath]: children }))
  }

  const chooseFolder = async () => {
    if (dirtyCount > 0 && !window.confirm('Discard unsaved changes before opening another folder?')) return
    const pickerWindow = window as Window & {
      showDirectoryPicker?: (options?: { mode: 'readwrite' }) => Promise<LocalDirectoryHandle>
    }
    if (!pickerWindow.showDirectoryPicker) {
      setStatus('Folder access requires a Chromium-based browser such as Edge or Chrome.')
      return
    }
    try {
      setBusy(true)
      const directory = await pickerWindow.showDirectoryPicker({ mode: 'readwrite' })
      setRootHandle(directory)
      setConversationHistory(loadWorkspaceHistory(directory.name))
      setOpenedFiles({})
      setActivePath('')
      setExpandedPaths(new Set(['']))
      setChildrenByPath({})
      await readChildren(directory, '')
      const gitClient = createWorkspaceGitClient(directory)
      const isRepository = await gitClient.isRepository()
      setGitInitialized(isRepository)
      setGitChanges(isRepository ? await gitClient.status() : [])
      setGitError('')
      setStatus(directory.name)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setStatus(`Could not open folder: ${errorMessage(error)}`)
    } finally {
      setBusy(false)
    }
  }

  const toggleDirectory = async (node: FileNode) => {
    if (node.handle.kind !== 'directory') return
    if (expandedPaths.has(node.path)) {
      setExpandedPaths((previous) => {
        const next = new Set(previous)
        next.delete(node.path)
        return next
      })
      return
    }
    setExpandedPaths((previous) => new Set(previous).add(node.path))
    if (!childrenByPath[node.path]) {
      try {
        await readChildren(node.handle, node.path)
      } catch (error) {
        setStatus(`Could not read folder: ${errorMessage(error)}`)
      }
    }
  }

  const openFile = async (node: FileNode) => {
    if (node.handle.kind !== 'file') return
    const existing = openedFiles[node.path]
    if (existing) {
      setActivePath(node.path)
      return
    }
    try {
      const file = await node.handle.getFile()
      if (file.size > MAX_FILE_BYTES) {
        setStatus(`${node.path} is larger than the 2 MB editor limit.`)
        return
      }
      const value = await file.text()
      if (value.includes('\0')) {
        setStatus(`${node.path} appears to be a binary file and cannot be edited as text.`)
        return
      }
      const fileHandle = node.handle
      setOpenedFiles((previous) => ({
        ...previous,
        [node.path]: {
          path: node.path,
          handle: fileHandle,
          value,
          savedValue: value,
          language: editorLanguage(node.path),
        },
      }))
      setActivePath(node.path)
      setStatus(`Opened ${node.path}`)
    } catch (error) {
      setStatus(`Could not open file: ${errorMessage(error)}`)
    }
  }

  const saveFile = async (path: string): Promise<void> => {
    const file = openedFiles[path]
    if (!file || file.value === file.savedValue) return
    try {
      const permission = await file.handle.requestPermission?.({ mode: 'readwrite' })
      if (permission && permission !== 'granted') {
        throw new Error(`Write permission was denied for ${path}. Reopen the folder and allow read/write access.`)
      }
      const writable = await file.handle.createWritable()
      await writable.write(file.value)
      await writable.close()
      setOpenedFiles((previous) => ({
        ...previous,
        [path]: { ...previous[path], savedValue: file.value },
      }))
      setStatus(`Saved ${path}`)
    } catch (error) {
      const message = `Could not save ${path}: ${errorMessage(error)}`
      setStatus(message)
      throw new Error(message)
    }
  }

  const saveActiveFile = () => {
    if (activePath) void saveFile(activePath).catch(() => {})
  }
  saveCurrentRef.current = saveActiveFile

  const saveAllFiles = async () => {
    setBusy(true)
    try {
      for (const path of openPaths) await saveFile(path)
    } catch {
      return
    } finally {
      setBusy(false)
    }
  }

  const appendConversation = (messages: WorkspaceChatMessage[]) => {
    if (!rootHandle) return
    const next = [...conversationHistory, ...messages].slice(-MAX_WORKSPACE_HISTORY).map((message) => ({
      role: message.role,
      content: message.content.slice(0, MAX_WORKSPACE_HISTORY_MESSAGE_CHARS),
    }))
    setConversationHistory(next)
    try {
      localStorage.setItem(`workspace_agent_history:${rootHandle.name}`, JSON.stringify(next))
    } catch {
      setAgentError('Could not save chat history in this browser.')
    }
  }

  const clearConversationHistory = () => {
    if (!rootHandle) return
    setConversationHistory([])
    localStorage.removeItem(`workspace_agent_history:${rootHandle.name}`)
  }

  const createFile = async () => {
    if (!rootHandle) return
    const name = window.prompt('New file name')?.trim()
    if (!name) return
    if (name.includes('/') || name.includes('\\') || name === '.' || name === '..') {
      setStatus('Enter a file name, not a path.')
      return
    }
    try {
      for await (const existing of rootHandle.values()) {
        if (existing.name === name) {
          setStatus(`${name} already exists in this folder.`)
          return
        }
      }
      const handle = await rootHandle.getFileHandle(name, { create: true })
      const writable = await handle.createWritable()
      await writable.write('')
      await writable.close()
      await readChildren(rootHandle, '')
      await openFile({ path: name, handle })
    } catch (error) {
      setStatus(`Could not create file: ${errorMessage(error)}`)
    }
  }

  const closeFile = (path: string) => {
    const file = openedFiles[path]
    if (file?.value !== file?.savedValue && !window.confirm(`Discard unsaved changes to ${path}?`)) return
    setOpenedFiles((previous) => {
      const next = { ...previous }
      delete next[path]
      return next
    })
    if (activePath === path) {
      const nextPath = openPaths.find((openPath) => openPath !== path) || ''
      setActivePath(nextPath)
    }
  }

  const refreshTree = async () => {
    if (!rootHandle) return
    try {
      const expanded = [...expandedPaths].filter(Boolean)
      setChildrenByPath({})
      await readChildren(rootHandle, '')
      for (const path of expanded) {
        try {
          let directory = rootHandle
          for (const part of path.split('/')) directory = await directory.getDirectoryHandle(part)
          await readChildren(directory, path)
        } catch (error) {
          if (!(error instanceof DOMException) || error.name !== 'NotFoundError') throw error
        }
      }
      setStatus(`Refreshed ${rootHandle.name}`)
    } catch (error) {
      setStatus(`Could not refresh folder: ${errorMessage(error)}`)
    }
  }

  const refreshGitStatus = async () => {
    if (!rootHandle) return
    setGitBusy(true)
    setGitError('')
    try {
      const gitClient = createWorkspaceGitClient(rootHandle)
      const isRepository = await gitClient.isRepository()
      setGitInitialized(isRepository)
      setGitChanges(isRepository ? await gitClient.status() : [])
      setStatus(isRepository ? 'Git status refreshed' : 'This folder is not a Git repository')
    } catch (error) {
      setGitError(errorMessage(error))
    } finally {
      setGitBusy(false)
    }
  }

  const initializeGit = async () => {
    if (!rootHandle) return
    setGitBusy(true)
    setGitError('')
    try {
      const permission = await rootHandle.requestPermission?.({ mode: 'readwrite' })
      if (permission && permission !== 'granted') throw new Error('Allow read/write access to this folder, then try again.')
      await createWorkspaceGitClient(rootHandle).initialize()
      setGitInitialized(true)
      setGitChanges(await createWorkspaceGitClient(rootHandle).status())
      setStatus('Git repository initialized')
    } catch (error) {
      setGitError(errorMessage(error))
    } finally {
      setGitBusy(false)
    }
  }

  const cloneRepository = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!rootHandle || gitBusy || !cloneUrl.trim()) return
    let repositoryUrl: URL
    try {
      repositoryUrl = new URL(cloneUrl.trim())
      if (repositoryUrl.protocol !== 'https:' || repositoryUrl.hostname !== 'github.com') {
        throw new Error('Use an HTTPS URL for a public GitHub repository.')
      }
    } catch (error) {
      setGitError(errorMessage(error))
      return
    }
    setGitBusy(true)
    setGitError('')
    try {
      const permission = await rootHandle.requestPermission?.({ mode: 'readwrite' })
      if (permission && permission !== 'granted') throw new Error('Allow read/write access to this folder, then try again.')
      for await (const entry of rootHandle.values()) {
        if (entry.name !== '.git') throw new Error('Choose an empty folder before cloning a repository.')
      }
      await createWorkspaceGitClient(rootHandle).clone(repositoryUrl.toString())
      setCloneUrl('')
      setGitInitialized(true)
      setGitChanges(await createWorkspaceGitClient(rootHandle).status())
      setChildrenByPath({})
      setExpandedPaths(new Set(['']))
      await readChildren(rootHandle, '')
      setStatus(`Cloned ${repositoryUrl.hostname}`)
    } catch (error) {
      setGitError(errorMessage(error))
      const isRepository = await createWorkspaceGitClient(rootHandle).isRepository()
      setGitInitialized(isRepository)
    } finally {
      setGitBusy(false)
    }
  }

  const commitChanges = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!rootHandle || !commitMessage.trim() || !gitAuthorName.trim() || !gitAuthorEmail.trim() || gitBusy) return
    setGitBusy(true)
    setGitError('')
    try {
      const permission = await rootHandle.requestPermission?.({ mode: 'readwrite' })
      if (permission && permission !== 'granted') throw new Error('Allow read/write access to this folder, then try again.')
      for (const path of openPaths) await saveFile(path)
      localStorage.setItem('workspace_git_author_name', gitAuthorName.trim())
      localStorage.setItem('workspace_git_author_email', gitAuthorEmail.trim())
      await createWorkspaceGitClient(rootHandle).commit(commitMessage.trim(), gitAuthorName.trim(), gitAuthorEmail.trim())
      setCommitMessage('')
      await refreshGitStatus()
      setStatus('Changes committed')
    } catch (error) {
      setGitError(errorMessage(error))
    } finally {
      setGitBusy(false)
    }
  }

  const runWorkspaceAgent = async (
    prompt: string,
    approvedRequirement = '',
    approvedPlan = '',
    priorToolResults: WorkspaceToolResult[] = [],
    priorInspectedFiles: WorkspaceContextFile[] = [],
  ) => {
    if (!rootHandle || !prompt.trim() || agentBusy) return
    setAgentBusy(true)
    setAgentError('')
    setAgentResult(null)
    setPendingWorkspaceChanges(null)
    try {
      setStatus(approvedPlan ? 'Preparing the approved plan for review...' : 'Analyzing project files and preparing a plan...')
      for (const path of openPaths) await saveFile(path)
      const scan = await scanWorkspace(rootHandle, openedFiles)
      if (scan.tooLargePath) {
        throw new Error(`Could not include the complete project context: ${scan.tooLargePath} exceeds the workspace context limit.`)
      }
      if (scan.files.length === 0) {
        throw new Error('No supported text or source files were found in this project.')
      }
      const toolResults = [...priorToolResults].slice(-4)
      let inspectedFiles = [...priorInspectedFiles]
      let context: SelectedWorkspaceContext | null = null
      let data: Record<string, any> | null = null
      setWorkspaceAgentRetry({ prompt, approvedRequirement, approvedPlan, toolResults, inspectedFiles })

      for (let round = 0; round <= 4; round += 1) {
        const filesByPath = new Map(scan.files.map((file) => [file.path, file]))
        for (const file of inspectedFiles) filesByPath.set(file.path, file)
        const projectFiles = [...filesByPath.values()]
        const contextPrompt = `${prompt}\n${approvedRequirement}\n${approvedPlan}`
        const priorities = pathsMentionedIn(contextPrompt, projectFiles)
        context = selectWorkspaceContext(projectFiles, contextPrompt, activePath, priorities)
        const incompletePriorityPaths = priorities.filter((path) => {
          const file = context?.files.find((candidate) => candidate.path === path)
          return !file || file.truncated
        })
        if (incompletePriorityPaths.length) {
          throw new Error(`Could not include the complete contents of planned files: ${incompletePriorityPaths.join(', ')}. Narrow the implementation plan and retry.`)
        }
        setWorkspaceAgentRetry({
          prompt,
          approvedRequirement,
          approvedPlan,
          toolResults: [...toolResults],
          inspectedFiles: [...inspectedFiles],
        })

        const response = await fetch(`${API_BASE}/api/workspace-agent/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: prompt.trim(),
            approved_requirement: approvedRequirement,
            approved_plan: approvedPlan,
            history: approvedPlan
              ? [...conversationHistory.slice(-(MAX_WORKSPACE_HISTORY - 1)), { role: 'user', content: `I approve this implementation plan:\n${approvedPlan}` }]
              : conversationHistory.slice(-MAX_WORKSPACE_HISTORY),
            tool_results: toolResults,
            model: selectedModel,
            inventory: context.inventory,
            directories: scan.directories,
            files: context.files,
          }),
        })
        const responseData: Record<string, any> = await response.json()
        data = responseData
        if (!response.ok) throw new Error(responseData.error || 'The workspace agent request failed.')
        if (responseData.mode !== 'tool_call') break
        if (round === 4 || toolResults.length >= 4) throw new Error('The agent reached its four-inspection limit. Narrow the request and try again.')

        const toolCall = responseData.tool_call as WorkspaceToolCall
        setStatus(toolCall.tool === 'read_file' ? `Reading ${toolCall.path}...` : `Searching workspace for ${toolCall.query}...`)
        const result = executeWorkspaceTool(toolCall, projectFiles, scan.directories)
        toolResults.push(result)
        if (toolCall.tool === 'read_file') {
          const file = projectFiles.find((candidate) => candidate.path === (toolCall.path || '').replace(/\\/g, '/'))
          if (file) {
            inspectedFiles = inspectedFiles.filter((candidate) => candidate.path !== file.path)
            inspectedFiles.push({
              path: file.path,
              content: file.content.slice(0, 20000),
              truncated: file.content.length > 20000,
            })
          }
        }
      }

      if (!context || !data) throw new Error('The workspace agent did not return a result.')

      if (data.mode === 'plan') {
        setWorkspaceAgentRetry(null)
        setAgentResult({
          type: 'plan',
          analysis: [
            data.analysis || '',
            data.discarded_unapproved_changes ? 'Unapproved edits were discarded. Approve the plan, then review the generated file changes.' : '',
          ].filter(Boolean).join('\n\n'),
          requirement: data.requirement || '',
          plan: data.plan || '',
          requestPrompt: prompt,
          toolResults,
          inspectedFiles,
        })
        appendConversation([
          { role: 'user', content: prompt },
          { role: 'assistant', content: [data.analysis, data.requirement, data.plan, ...toolResults.map((result) => result.result)].filter(Boolean).join('\n\n') },
        ])
        setStatus('Review the agent plan, then approve it to generate a file diff.')
      } else if (data.mode === 'changes') {
        setWorkspaceAgentRetry(null)
        if (!Array.isArray(data.changes)) throw new Error('The agent returned an invalid file change set.')
        const changes = data.changes as WorkspaceFileChange[]
        const analyzedFiles = new Map([...context.files, ...inspectedFiles].filter((file) => !file.truncated).map((file) => [file.path, file.content]))
        setPendingWorkspaceChanges({
          changes,
          analyzedFiles,
          analyzedDirectories: new Set(scan.directories),
          analysis: data.analysis || '',
          plan: approvedPlan,
          requirement: approvedRequirement,
        })
        setAgentResult({ type: 'review', analysis: data.analysis || '' })
        setStatus('Review the proposed file changes before applying them.')
      } else if (data.mode === 'answer') {
        setWorkspaceAgentRetry(null)
        setAgentResult({ type: 'chat', message: data.message || data.analysis || '' })
        appendConversation([
          { role: 'user', content: prompt },
          { role: 'assistant', content: data.message || data.analysis || '' },
        ])
        setStatus(`Agent analyzed ${scan.files.length} project files`)
      } else {
        throw new Error('The workspace agent returned an unknown response type.')
      }
    } catch (error) {
      setAgentError(errorMessage(error))
      setStatus('Workspace agent request failed')
    } finally {
      setAgentBusy(false)
    }
  }

  const askAgent = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void runWorkspaceAgent(agentPrompt)
  }

  const retryWorkspaceAgent = () => {
    if (!workspaceAgentRetry) return
    void runWorkspaceAgent(
      workspaceAgentRetry.prompt,
      workspaceAgentRetry.approvedRequirement,
      workspaceAgentRetry.approvedPlan,
      workspaceAgentRetry.toolResults,
      workspaceAgentRetry.inspectedFiles,
    )
  }

  const suggestImprovement = () => {
    void runWorkspaceAgent('Analyze this project and propose one specific, high-value improvement that fits its existing architecture. Return a plan only; do not generate code until I approve the plan.')
  }

  const approveWorkspacePlan = () => {
    if (agentResult?.type !== 'plan' || !agentResult.plan) return
    void runWorkspaceAgent(
      agentResult.requestPrompt || agentPrompt,
      agentResult.requirement || '',
      agentResult.plan,
      agentResult.toolResults || [],
      agentResult.inspectedFiles || [],
    )
  }

  const applyWorkspaceChanges = async () => {
    if (!rootHandle || !pendingWorkspaceChanges || agentBusy) return
    setAgentBusy(true)
    setAgentError('')
    try {
      const permission = await rootHandle.requestPermission?.({ mode: 'readwrite' })
      if (permission && permission !== 'granted') throw new Error('Allow read/write access to this folder, then retry applying the changes.')
      await writeWorkspaceChanges(
        rootHandle,
        pendingWorkspaceChanges.changes,
        pendingWorkspaceChanges.analyzedFiles,
        pendingWorkspaceChanges.analyzedDirectories,
        openedFiles,
        setOpenedFiles,
        refreshTree,
      )
      if (gitInitialized) setGitChanges(await createWorkspaceGitClient(rootHandle).status())
      const changedPaths = pendingWorkspaceChanges.changes.map((change) => change.path)
      setAgentResult({ type: 'coding', analysis: pendingWorkspaceChanges.analysis, changedPaths })
      appendConversation([{
        role: 'assistant',
        content: `Implemented the approved plan: ${pendingWorkspaceChanges.requirement || pendingWorkspaceChanges.plan}\nUpdated files: ${changedPaths.join(', ')}`,
      }])
      setPendingWorkspaceChanges(null)
      setStatus(`Applied ${changedPaths.length} reviewed file change${changedPaths.length === 1 ? '' : 's'}`)
    } catch (error) {
      setAgentError(errorMessage(error))
      setStatus('Could not apply the reviewed workspace changes')
    } finally {
      setAgentBusy(false)
    }
  }

  const renderNode = (node: FileNode, depth = 0) => {
    const isDirectory = node.handle.kind === 'directory'
    const expanded = expandedPaths.has(node.path)
    return (
      <div key={node.path}>
        <button
          className={`workspace-tree-row${activePath === node.path ? ' is-active' : ''}`}
          style={{ paddingLeft: 10 + depth * 14 }}
          onClick={() => isDirectory ? void toggleDirectory(node) : void openFile(node)}
          disabled={agentBusy}
          title={node.path}
        >
          <span className="workspace-tree-icon">{isDirectory ? (expanded ? '▾' : '▸') : ' '}</span>
          <span className="workspace-tree-kind">{isDirectory ? '▰' : '·'}</span>
          <span className="workspace-tree-name">{node.handle.name}</span>
        </button>
        {isDirectory && expanded && (childrenByPath[node.path] || []).map((child) => renderNode(child, depth + 1))}
      </div>
    )
  }

  return (
    <section className="workspace-panel">
      <aside className="workspace-sidebar">
        <div className="workspace-sidebar-head">
          <span>EXPLORER</span>
          <div className="workspace-sidebar-actions">
            <button onClick={() => void createFile()} disabled={!rootHandle || agentBusy} title="New file">＋</button>
            <button onClick={() => void refreshTree()} disabled={!rootHandle || agentBusy} title="Refresh files">↻</button>
          </div>
        </div>
        {rootHandle ? (
          <div className="workspace-tree">
            <div className="workspace-root-name">▾ {rootHandle.name}</div>
            {(childrenByPath[''] || []).map((node) => renderNode(node))}
          </div>
        ) : (
          <div className="workspace-sidebar-empty">No folder selected</div>
        )}
        <div className="workspace-sidebar-footer">
          <span className={`workspace-permission-dot${rootHandle ? ' is-connected' : ''}`} />
          {rootHandle ? 'Local folder connected' : 'Local folder access'}
        </div>
      </aside>

      <div className="workspace-main">
        <header className="workspace-toolbar">
          <div className="workspace-location" title={rootHandle?.name || 'No folder open'}>
            <span>⌂</span>
            <span>{rootHandle?.name || 'Workspace'}</span>
            {activePath && <><span className="workspace-path-separator">/</span><span>{activePath}</span></>}
          </div>
          <div className="workspace-toolbar-actions">
            <span className="workspace-dirty-count">{dirtyCount ? `${dirtyCount} unsaved` : ''}</span>
            <button className="workspace-button workspace-button-secondary" onClick={() => setGitOpen((open) => !open)} disabled={!rootHandle}>
              {gitOpen ? 'Close Git' : 'Git'}{gitInitialized && gitChanges.length > 0 ? ` · ${gitChanges.length}` : ''}
            </button>
            <button className="workspace-button workspace-button-secondary" onClick={() => setAgentOpen((open) => !open)} disabled={!rootHandle || agentBusy}>
              {agentOpen ? 'Close agent' : 'Ask agent'}
            </button>
            <button className="workspace-button workspace-button-secondary" onClick={() => void saveAllFiles()} disabled={!dirtyCount || busy || agentBusy}>
              Save all
            </button>
            <button className="workspace-button workspace-button-primary" onClick={() => void chooseFolder()} disabled={busy || agentBusy}>
              Open folder
            </button>
          </div>
        </header>

        {gitOpen && rootHandle && (
          <section className="workspace-git-panel" aria-label="Git version control">
            <div className="workspace-git-heading">
              <strong>{gitInitialized ? 'Source Control' : 'Git repository'}</strong>
              <button className="workspace-button workspace-button-secondary" onClick={() => void refreshGitStatus()} disabled={gitBusy || !gitInitialized}>
                Refresh
              </button>
            </div>
            {!gitInitialized ? (
              <div className="workspace-git-setup">
                <button className="workspace-button workspace-button-primary" onClick={() => void initializeGit()} disabled={gitBusy}>
                  Initialize repository
                </button>
                <form className="workspace-git-clone" onSubmit={(event) => void cloneRepository(event)}>
                  <input aria-label="Git repository URL" type="url" value={cloneUrl} onChange={(event) => setCloneUrl(event.target.value)} placeholder="https://github.com/owner/repository.git" />
                  <button className="workspace-button workspace-button-secondary" type="submit" disabled={gitBusy || !cloneUrl.trim()}>
                    {gitBusy ? 'Cloning...' : 'Clone'}
                  </button>
                </form>
              </div>
            ) : (
              <>
                <form className="workspace-git-commit" onSubmit={(event) => void commitChanges(event)}>
                  <input value={commitMessage} onChange={(event) => setCommitMessage(event.target.value)} aria-label="Commit message" placeholder="Commit message" maxLength={200} />
                  <input value={gitAuthorName} onChange={(event) => setGitAuthorName(event.target.value)} aria-label="Git author name" placeholder="Author name" maxLength={80} />
                  <input value={gitAuthorEmail} onChange={(event) => setGitAuthorEmail(event.target.value)} aria-label="Git author email" placeholder="Author email" type="email" maxLength={200} />
                  <button className="workspace-button workspace-button-primary" type="submit" disabled={gitBusy || !gitChanges.length || !commitMessage.trim() || !gitAuthorName.trim() || !gitAuthorEmail.trim()}>
                    Commit all
                  </button>
                </form>
                {gitChanges.length ? (
                  <ul className="workspace-git-changes">
                    {gitChanges.map((change) => <li key={change.path}><span>{change.path}</span><span>{change.status}</span></li>)}
                  </ul>
                ) : <p className="workspace-git-clean">Working tree clean</p>}
              </>
            )}
            {gitError && <div className="workspace-git-error" role="alert">{gitError}</div>}
            <p className="workspace-git-note">Status checks saved files on disk. Commit saves open editor changes first.</p>
          </section>
        )}

        <div className="workspace-editor-shell">
          {openPaths.length > 0 && (
            <div className="workspace-tabs" role="tablist" aria-label="Open files">
              {openPaths.map((path) => (
                <div key={path} className={`workspace-file-tab${activePath === path ? ' is-active' : ''}`}>
                  <button role="tab" aria-selected={activePath === path} onClick={() => setActivePath(path)} title={path}>
                    {openedFiles[path].value !== openedFiles[path].savedValue && <span className="workspace-unsaved-dot" />}
                    <span>{path.split('/').pop()}</span>
                  </button>
                  <button className="workspace-close-tab" onClick={() => closeFile(path)} aria-label={`Close ${path}`} title="Close file">×</button>
                </div>
              ))}
            </div>
          )}

          {activeFile ? (
            <div className="workspace-editor">
              <Editor
                path={activeFile.path}
                language={activeFile.language}
                theme="vs-dark"
                value={activeFile.value}
                onChange={(value) => setOpenedFiles((previous) => ({
                  ...previous,
                  [activePath]: { ...previous[activePath], value: value ?? '' },
                }))}
                onMount={(editor, monaco) => {
                  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => saveCurrentRef.current())
                }}
                options={{
                  automaticLayout: true,
                    readOnly: agentBusy,
                  fontSize: 14,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  tabSize: 2,
                  wordWrap: 'on',
                  padding: { top: 12 },
                }}
              />
            </div>
          ) : (
            <div className="workspace-empty-editor">
              <div className="workspace-empty-mark">{rootHandle ? '⌘' : '⌂'}</div>
              <div>{rootHandle ? 'Select a file from the explorer' : 'Open a local folder'}</div>
              {!rootHandle && <button className="workspace-button workspace-button-primary" onClick={() => void chooseFolder()} disabled={busy}>Choose folder</button>}
            </div>
          )}
        </div>

        {agentOpen && (
          <section className="workspace-agent-panel" aria-label="Workspace agent">
            {conversationHistory.length > 0 && (
              <div className="workspace-agent-history" role="log" aria-label="Workspace chat history">
                <div className="workspace-agent-history-heading">
                  <span>Conversation · {conversationHistory.length} messages</span>
                  <button className="workspace-button workspace-button-secondary" type="button" onClick={clearConversationHistory} disabled={agentBusy}>
                    Clear history
                  </button>
                </div>
                {conversationHistory.map((message, index) => (
                  <div className={`workspace-agent-message is-${message.role}`} key={`${index}-${message.role}`}>
                    <strong>{message.role === 'user' ? 'You' : 'Agent'}</strong>
                    <pre>{message.content}</pre>
                  </div>
                ))}
              </div>
            )}
            <form className="workspace-agent-form" onSubmit={(event) => void askAgent(event)}>
              <label htmlFor="workspace-agent-prompt">Ask about this project</label>
              <select
                className="workspace-model-select"
                aria-label="Workspace agent model"
                value={selectedModel}
                onChange={(event) => {
                  setSelectedModel(event.target.value)
                  localStorage.setItem('workspace_selected_model', event.target.value)
                }}
              >
                {Object.entries(modelGroups).map(([group, models]) => (
                  <optgroup key={group} label={group}>
                    {models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}
                  </optgroup>
                ))}
              </select>
              <div className="workspace-agent-composer">
                <textarea
                  id="workspace-agent-prompt"
                  value={agentPrompt}
                  onChange={(event) => setAgentPrompt(event.target.value)}
                  placeholder="Ask for a change, explanation, or code review..."
                  maxLength={5000}
                  rows={2}
                />
                <button className="workspace-button workspace-button-primary" type="submit" disabled={agentBusy || !agentPrompt.trim()}>
                  {agentBusy ? 'Working...' : 'Send'}
                </button>
                <button className="workspace-button workspace-button-secondary" type="button" onClick={suggestImprovement} disabled={agentBusy}>
                  Suggest improvement
                </button>
              </div>
              <div className="workspace-agent-meta">
                Project text files are scanned automatically; generated lockfiles, hidden dependency/build folders, and secret files are excluded. Unsaved edits override disk contents.
              </div>
            </form>
            {agentError && (
              <div className="workspace-agent-error" role="alert">
                <span>{agentError}</span>
                {workspaceAgentRetry && (
                  <button className="workspace-button workspace-button-secondary" type="button" onClick={retryWorkspaceAgent} disabled={agentBusy}>
                    Retry
                  </button>
                )}
              </div>
            )}
            {agentResult && (
              <div className="workspace-agent-result">
                {agentResult.type === 'chat' && agentResult.message && <section><h3>Answer</h3><pre>{agentResult.message}</pre></section>}
                {agentResult.analysis && agentResult.type !== 'chat' && <section><h3>Project analysis</h3><pre>{agentResult.analysis}</pre></section>}
                {agentResult.type === 'plan' && agentResult.requirement && (
                  <section>
                    <h3>Requirement</h3>
                    <pre>{agentResult.requirement}</pre>
                  </section>
                )}
                {agentResult.type === 'plan' && agentResult.plan && (
                  <section>
                    <h3>Implementation plan</h3>
                    <pre>{agentResult.plan}</pre>
                    <button className="workspace-button workspace-button-primary workspace-agent-approve" onClick={approveWorkspacePlan} disabled={agentBusy}>
                      Approve plan, generate changes
                    </button>
                  </section>
                )}
                {agentResult.type === 'review' && pendingWorkspaceChanges && (
                  <section>
                    <h3>Review file changes</h3>
                    <div className="workspace-agent-diff-list">
                      {pendingWorkspaceChanges.changes.map((change) => {
                        const original = pendingWorkspaceChanges.analyzedFiles.get(change.path)
                        return (
                          <details key={change.path} className="workspace-agent-diff">
                            <summary>{change.action === 'delete_directory' ? 'Remove folder' : change.action === 'delete' ? 'Delete file' : original === undefined ? 'New file' : 'Update file'} · {change.path}</summary>
                            <div className="workspace-agent-diff-content">
                              {original !== undefined && <pre className="workspace-agent-diff-before">{original}</pre>}
                              {change.action === 'delete_directory'
                                ? <div className="workspace-agent-diff-delete">This folder will be removed after all reviewed child entries are removed.</div>
                                : change.action === 'delete'
                                  ? <div className="workspace-agent-diff-delete">This file will be removed.</div>
                                : <pre className="workspace-agent-diff-after">{change.content}</pre>}
                            </div>
                          </details>
                        )
                      })}
                    </div>
                    <div className="workspace-agent-review-actions">
                      <button className="workspace-button workspace-button-primary" onClick={() => void applyWorkspaceChanges()} disabled={agentBusy}>
                        {agentBusy ? 'Applying...' : 'Apply changes'}
                      </button>
                      <button className="workspace-button workspace-button-secondary" onClick={() => { setPendingWorkspaceChanges(null); setAgentResult(null) }} disabled={agentBusy}>
                        Discard changes
                      </button>
                    </div>
                  </section>
                )}
                {agentResult.type === 'coding' && agentResult.changedPaths && (
                  <section>
                    <h3>Updated files</h3>
                    <ul className="workspace-agent-changed-files">
                      {agentResult.changedPaths.map((path) => <li key={path}>{path}</li>)}
                    </ul>
                  </section>
                )}
                {agentResult.type === 'chat' && !agentResult.message && <p>The agent returned no output.</p>}
              </div>
            )}
          </section>
        )}

        <footer className="workspace-statusbar">
          <span>{status}</span>
          {activeFile && <span>{activeFile.language} · UTF-8</span>}
        </footer>
      </div>
    </section>
  )
}

function loadWorkspaceHistory(workspaceName: string): WorkspaceChatMessage[] {
  try {
    const saved = localStorage.getItem(`workspace_agent_history:${workspaceName}`)
    const history: unknown = saved ? JSON.parse(saved) : []
    if (!Array.isArray(history)) return []
    return history.filter((message): message is WorkspaceChatMessage =>
      Boolean(message) &&
      (message.role === 'user' || message.role === 'assistant') &&
      typeof message.content === 'string'
    ).slice(-MAX_WORKSPACE_HISTORY).map((message) => ({
      role: message.role,
      content: message.content.slice(0, MAX_WORKSPACE_HISTORY_MESSAGE_CHARS),
    }))
  } catch {
    return []
  }
}