import { useState, useRef, useEffect, useCallback } from 'react'
import type { AgentStatus } from '../types'

const INITIAL_AGENTS: AgentStatus[] = [
  { role: 'coder', id: 'coder-a1b2c3', running: true, currentTask: null, tasksCompleted: 28, lastResult: null },
]

const AGENT_COLORS: Record<string, string> = {
  coder: 'var(--accent-blue)',
}

type EntryResult =
  | { type: 'chat'; message: string }
  | { type: 'coding'; code: string; review: string; tests: string; duration: number; error?: string }
  | { type: 'debug'; errorType: string; analysis: string; fix: string; code: string }
  | { type: 'plan'; plan: string }
  | { type: 'research'; research: string }
  | { type: 'image'; imageData: string; mimeType: string; error?: string }

interface ConversationEntry {
  id: number
  prompt: string
  result: EntryResult
  timestamp: number
}

interface Session {
  id: string
  name: string
  conversation: ConversationEntry[]
  activeTab: Record<number, 'code' | 'review' | 'tests'>
  createdAt: number
  updatedAt: number
}

const API_BASE = 'http://localhost:8000'
const STORAGE_KEY = 'agent_sessions'

const CODING_KEYWORDS = [
  'write', 'code', 'function', 'implement', 'bug', 'fix', 'test', 'algorithm',
  'program', 'class', 'method', 'variable', 'debug', 'compile', 'refactor',
  'sort', 'search', 'reverse', 'traverse', 'recursion', 'iterate', 'parse',
  'generate', 'create', 'build', 'make', 'add', 'remove', 'update', 'delete',
  'api', 'endpoint', 'route', 'database', 'sql', 'query', 'array', 'string',
  'list', 'map', 'filter', 'reduce', 'loop', 'callback', 'promise', 'async',
  'await', 'import', 'export', 'return', 'throw', 'try', 'catch',
  'python', 'javascript', 'java', 'typescript', 'rust', 'golang', 'cpp', 'c++',
  'solution', 'leetcode', 'hackerrank', 'solve', 'valid', 'validate',
]

function _detectLanguage(prompt: string): string {
  const lower = prompt.toLowerCase().trim()
  const patterns: { lang: string; regex: RegExp }[] = [
    { lang: 'javascript', regex: /\bin javascript\b/ },
    { lang: 'javascript', regex: /\busing javascript\b/ },
    { lang: 'typescript', regex: /\bin typescript\b/ },
    { lang: 'typescript', regex: /\busing typescript\b/ },
    { lang: 'java', regex: /\bin java\b/ },
    { lang: 'java', regex: /\busing java\b/ },
    { lang: 'python', regex: /\bin python\b/ },
    { lang: 'python', regex: /\busing python\b/ },
    { lang: 'cpp', regex: /\bin cpp\b/ },
    { lang: 'cpp', regex: /\busing cpp\b/ },
    { lang: 'go', regex: /\bin go\b/ },
    { lang: 'go', regex: /\busing go\b/ },
    { lang: 'rust', regex: /\bin rust\b/ },
    { lang: 'rust', regex: /\busing rust\b/ },
  ]
  for (const { lang, regex } of patterns) {
    if (regex.test(lower)) return lang
  }
  return 'python'
}

function classifyPrompt(text: string): 'chat' | 'coding' | 'debug' {
  const lower = text.toLowerCase().trim()
  const errorPatterns = [
    /\b(Traceback|Error:|Exception:|SyntaxError|TypeError|NameError|IndexError)\b/i,
    /\b(KeyError|ValueError|AttributeError|ImportError|ModuleNotFoundError)\b/i,
    /\b(FileNotFoundError|ZeroDivisionError|RecursionError|RuntimeError)\b/i,
    /\b(IndentationError|StopIteration|ConnectionError|TimeoutError)\b/i,
    /File ".*?", line \d+/,
    /(undefined|is not defined|out of range|unexpected token)/i,
    /(can't|cannot) (resolve|find|import|access)/i,
    /does not (exist|have|contain)/i,
    /(fix|debug|error|bug|broken|not working)/i,
  ]
  const errorScore = errorPatterns.filter((p) => p.test(text)).length
  const chatPatterns = [
    /^(hello|hi|hey|heya|howdy|sup|yo|greetings)\b/i,
    /^(bye|goodbye|cya|see ya|see you|later)\b/i,
    /^(thanks|thank you|ty|thx)\b/i,
    /^(who are you|what are you|tell me about)/i,
    /^(what can you do|help|capabilities|features)/i,
    /^how (are you|is it going|do you feel)/i,
  ]
  for (const p of chatPatterns) {
    if (p.test(text)) return 'chat'
  }
  if (errorScore >= 1) return 'debug'
  const directCodingRequest = /^(?:please\s+)?(?:write|implement|create|build|fix|debug|refactor|generate|review|test|add|remove|update|delete|modify|change)\b/i
  const askedCodingRequest = /^(?:can|could|would)\s+you\s+(?:please\s+)?(?:help me\s+)?(?:write|implement|create|build|fix|debug|refactor|generate|review|test|add|remove|update|delete|modify|change)\b/i
  if (directCodingRequest.test(text) || askedCodingRequest.test(text)) return 'coding'
  if (/^(?:what|which|why|how|when|where|who|is|are|do|does|did|can|could|would|should)\b/i.test(text)) return 'chat'
  const codingScore = CODING_KEYWORDS.filter((kw) => lower.includes(kw)).length
  if (codingScore >= 2) return 'coding'
  if (codingScore >= 1) return 'coding'
  // Long messages with code-like structure are likely coding problems
  if (text.length > 200 && /\b(Input:|Output:|Example|board|array|list|string|int|function)\b/i.test(text)) return 'coding'
  return 'chat'
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function makeSession(name?: string): Session {
  const id = generateId()
  return {
    id,
    name: name || `Chat ${new Date().toLocaleDateString()}`,
    conversation: [],
    activeTab: {},
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
}

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

function saveSessions(sessions: Session[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch { /* ignore */ }
}

function sessionPreview(s: Session): string {
  const last = s.conversation[s.conversation.length - 1]
  if (!last) return 'Empty chat'
  const text = last.prompt.length > 40 ? last.prompt.slice(0, 40) + '…' : last.prompt
  return text
}

export default function AgentPanel() {
  const [agents, setAgents] = useState<AgentStatus[]>(INITIAL_AGENTS)
  const [prompt, setPrompt] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [currentStatus, setCurrentStatus] = useState('')
  const [conversation, setConversation] = useState<ConversationEntry[]>([])
  const [activeTab, setActiveTab] = useState<Record<number, 'code' | 'review' | 'tests'>>({})
  const [sessions, setSessions] = useState<Session[]>(() => {
    const loaded = loadSessions()
    return loaded.length > 0 ? loaded : [makeSession('Chat 1')]
  })
  const [activeSessionId, setActiveSessionId] = useState<string>(() => sessions[0]?.id || '')
  const [archivedSessions, setArchivedSessions] = useState<Session[]>(() => {
    try {
      const raw = localStorage.getItem('agent_sessions_archived')
      return raw ? JSON.parse(raw) : []
    } catch { return [] }
  })
  const [showArchived, setShowArchived] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedModel, setSelectedModel] = useState('gemini-3.1-flash-lite')
  const [selectedAgents, setSelectedAgents] = useState<string[]>(['coder'])
  const [selectedService, setSelectedService] = useState('auto')
  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [availableModels, setAvailableModels] = useState<{id: string; name: string; group?: string; daily_limit?: number}[]>([])
  const [modelUsage, setModelUsage] = useState<Record<string, {used: number; limit: number; percent: number; remaining: number}>>({})
  const [webSearchEnabled, setWebSearchEnabled] = useState(true)
  const [planningMode, setPlanningMode] = useState(false)
  const [researchMode, setResearchMode] = useState(false)
  const [pendingPlan, setPendingPlan] = useState<string | null>(null)
  const [pendingPlanPrompt, setPendingPlanPrompt] = useState('')
  const [generatedImage, setGeneratedImage] = useState<{imageData: string; mimeType: string; prompt: string} | null>(null)
  const [showAddMenu, setShowAddMenu] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [snipMode, setSnipMode] = useState<{dataUrl: string} | null>(null)
  const [snipRect, setSnipRect] = useState<{x: number; y: number; w: number; h: number} | null>(null)
  const [snipStart, setSnipStart] = useState<{x: number; y: number} | null>(null)
  const [recording, setRecording] = useState(false)
  const recordingRef = useRef(false)
  const recognitionRef = useRef<any>(null)
  const transcriptRef = useRef('')
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)
  const animFrameRef = useRef(0)
  const micStreamRef = useRef<MediaStream | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const snipImgRef = useRef<HTMLImageElement>(null)
  const addMenuRef = useRef<HTMLDivElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  let entryId = useRef(0)

  // Close add menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setShowAddMenu(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const activeSession = sessions.find((s) => s.id === activeSessionId)

  // Sync conversation state from active session on mount and session switch
  useEffect(() => {
    const active = sessions.find((s) => s.id === activeSessionId)
    if (active) {
      setConversation(active.conversation)
      setActiveTab(active.activeTab)
    }
  }, [activeSessionId, sessions]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    saveSessions(sessions)
  }, [sessions])

  useEffect(() => {
    try {
      localStorage.setItem('agent_sessions_archived', JSON.stringify(archivedSessions))
    } catch { /* ignore */ }
  }, [archivedSessions])

  const fetchUsage = useCallback(() => {
    fetch(`${API_BASE}/api/usage/`)
      .then((r) => r.json())
      .then((d) => setModelUsage(d.usage || {}))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/api/models/`)
      .then((r) => r.json())
      .then((d) => {
        setAvailableModels(d.models || [])
        if (d.current) setSelectedModel(d.current)
      })
      .catch(() => {})
    fetchUsage()
    const interval = setInterval(fetchUsage, 30000)
    return () => clearInterval(interval)
  }, [fetchUsage])

  const switchSession = useCallback((id: string) => {
    if (id === activeSessionId) return
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, conversation, activeTab, updatedAt: Date.now() }
          : s
      )
    )
    const target = sessions.find((s) => s.id === id)
    if (target) {
      setConversation(target.conversation)
      setActiveTab(target.activeTab)
      setPrompt('')
    }
    setActiveSessionId(id)
  }, [activeSessionId, conversation, activeTab, sessions])

  const newSession = useCallback(() => {
    const newS = makeSession(`Chat ${sessions.length + 1}`)
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, conversation, activeTab, updatedAt: Date.now() }
          : s
      ).concat(newS)
    )
    setActiveSessionId(newS.id)
    setConversation([])
    setActiveTab({})
    setPrompt('')
  }, [activeSessionId, conversation, activeTab, sessions.length])

  const deleteSession = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (sessions.length <= 1) return
    const session = sessions.find((s) => s.id === id)
    if (session) {
      setArchivedSessions((prev) => [session, ...prev])
    }
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (id === activeSessionId) {
      const remaining = sessions.filter((s) => s.id !== id)
      const next = remaining[0]
      if (next) {
        setActiveSessionId(next.id)
        setConversation(next.conversation)
        setActiveTab(next.activeTab)
        setPrompt('')
      }
    }
  }, [sessions, activeSessionId])

  const restoreSession = useCallback((session: Session) => {
    setSessions((prev) => [session, ...prev])
    setArchivedSessions((prev) => prev.filter((s) => s.id !== session.id))
    setActiveSessionId(session.id)
    setConversation(session.conversation)
    setActiveTab(session.activeTab)
    setPrompt('')
    setShowArchived(false)
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  const appendToConversation = useCallback((entry: ConversationEntry) => {
    setConversation((prev) => [...prev, entry])
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, conversation: [...s.conversation, entry], updatedAt: Date.now() }
          : s
      )
    )
  }, [activeSessionId])

  const updateLastEntry = useCallback((entryId: number, result: EntryResult) => {
    setConversation((prev) =>
      prev.map((e) => (e.id === entryId ? { ...e, result } : e))
    )
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, conversation: s.conversation.map((e) => (e.id === entryId ? { ...e, result } : e)), updatedAt: Date.now() }
          : s
      )
    )
  }, [activeSessionId])

  const updateActiveTab = useCallback((id: number, tab: 'code' | 'review' | 'tests') => {
    setActiveTab((prev) => {
      const next = { ...prev, [id]: tab }
      setSessions((sPrev) =>
        sPrev.map((s) =>
          s.id === activeSessionId ? { ...s, activeTab: next, updatedAt: Date.now() } : s
        )
      )
      return next
    })
  }, [activeSessionId])

  const addLog = (msg: string) => {
    setLogs((prev) => [msg, ...prev].slice(0, 50))
  }

  const setAgentTask = (role: string, task: string | null) => {
    setAgents((prev) =>
      prev.map((a) => (a.role === role ? { ...a, currentTask: task } : a))
    )
  }

  const incrementTasks = (role: string, lastResult: string | null = null) => {
    setAgents((prev) =>
      prev.map((a) =>
        a.role === role
          ? { ...a, currentTask: null, tasksCompleted: a.tasksCompleted + 1, lastResult }
          : a
      )
    )
  }

  const executePendingPlan = async () => {
    if (!pendingPlan || !pendingPlanPrompt) return
    const desc = pendingPlanPrompt
    const entryIdNum = ++entryId.current
    setPendingPlan(null)
    setPendingPlanPrompt('')
    setLoading(true)

    const history = conversation.slice(-10).map((e) => ({
      prompt: e.prompt,
      result: e.result,
    }))

    addLog(`[Orchestrator] Executing plan for: "${desc.slice(0, 40)}"`)
    try {
      const res = await fetch(`${API_BASE}/api/workflow/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: desc, history,
          model: selectedModel,
          agents: selectedAgents,
          service: selectedService,
          plan: pendingPlan,
          plan_approved: true,
        }),
      })
      const data = await res.json()
      if (data.success) {
        appendToConversation({
          id: entryIdNum,
          prompt: desc,
          result: {
            type: 'coding',
            code: data.code || '',
            review: data.review || '',
            tests: data.tests || '',
            duration: data.duration || 0,
          },
          timestamp: Date.now(),
        })
        updateActiveTab(entryIdNum, 'code')
      } else {
        appendToConversation({
          id: entryIdNum,
          prompt: desc,
          result: { type: 'chat', message: `Plan execution failed: ${data.error}` },
          timestamp: Date.now(),
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      appendToConversation({
        id: entryIdNum,
        prompt: desc,
        result: { type: 'chat', message: `Plan execution failed: ${msg}` },
        timestamp: Date.now(),
      })
    }
    setLoading(false)
    inputRef.current?.focus()
  }

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  }

  const sendMessage = async () => {
    if (!prompt.trim() && attachedFiles.length === 0) return
    // Image generation mode
    if (prompt.trim().toLowerCase().startsWith('/image ') || prompt.trim().toLowerCase().startsWith('🎨 ')) {
      const imgPrompt = prompt.trim().replace(/^\/image\s+/i, '').replace(/^🎨\s+/, '')
      if (imgPrompt) {
        setLoading(true)
        setCurrentStatus('🎨 Generating image...')
        setPrompt('')
        // Add placeholder entry with pixel animation
        const placeholderId = ++entryId.current
        appendToConversation({
          id: placeholderId,
          prompt: `🎨 ${imgPrompt}`,
          result: { type: 'chat', message: '' },
          timestamp: Date.now(),
        })
        try {
          const res = await fetch(`${API_BASE}/api/image/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: imgPrompt, model: selectedModel }),
          })
          const data = await res.json()
          // Replace placeholder with real result
          setConversation((prev) => prev.filter((e) => e.id !== placeholderId))
          setSessions((prev) =>
            prev.map((s) => ({
              ...s,
              conversation: s.conversation.filter((e) => e.id !== placeholderId),
            }))
          )
          if (data.success) {
            appendToConversation({
              id: ++entryId.current,
              prompt: `🎨 ${imgPrompt}`,
              result: { type: 'image', imageData: data.image_data, mimeType: data.mime_type },
              timestamp: Date.now(),
            })
          } else {
            appendToConversation({
              id: ++entryId.current,
              prompt: `🎨 ${imgPrompt}`,
              result: { type: 'chat', message: `Image generation failed: ${data.error || 'Unknown error'}` },
              timestamp: Date.now(),
            })
          }
        } catch (err: unknown) {
          setConversation((prev) => prev.filter((e) => e.id !== placeholderId))
          setSessions((prev) =>
            prev.map((s) => ({
              ...s,
              conversation: s.conversation.filter((e) => e.id !== placeholderId),
            }))
          )
          const msg = err instanceof Error ? err.message : 'Unknown error'
          appendToConversation({
            id: ++entryId.current,
            prompt: `🎨 ${imgPrompt}`,
            result: { type: 'chat', message: `Image generation failed: ${msg}` },
            timestamp: Date.now(),
          })
        }
        setLoading(false)
        setCurrentStatus('')
        inputRef.current?.focus()
        return
      }
    }

    const desc = prompt.trim()
    const entryIdNum = ++entryId.current
    const mode = classifyPrompt(desc)
    setPrompt('')
    setLoading(true)

    // Show user prompt immediately
    const userEntry: ConversationEntry = {
      id: entryIdNum,
      prompt: desc,
      result: { type: 'chat', message: '' },
      timestamp: Date.now(),
    }
    appendToConversation(userEntry)
    setCurrentStatus(mode === 'chat' ? '💬 Thinking...' : mode === 'debug' ? '🔍 Analyzing error...' : '🤔 Processing...')

    // Build history from current conversation (last 10 entries)
    const history = conversation.slice(-10).map((e) => ({
      prompt: e.prompt,
      result: e.result,
    }))

    const commonBody: Record<string, unknown> = {
      model: selectedModel,
      agents: selectedAgents,
      service: selectedService,
      web_search: webSearchEnabled,
      research_mode: researchMode,
    }

    if (planningMode && !pendingPlan) {
      commonBody.agents = [...selectedAgents.filter(a => a !== 'planner'), 'planner']
    }

    // Handle file uploads
    if (attachedFiles.length > 0) {
      try {
        const formData = new FormData()
        formData.append('file', attachedFiles[0])
        formData.append('prompt', desc || `Process file: ${attachedFiles[0].name}`)
        formData.append('model', selectedModel)
        formData.append('service', selectedService)
        formData.append('web_search', String(webSearchEnabled))
        formData.append('research_mode', String(researchMode))
        if (pendingPlan) formData.append('plan', pendingPlan)
        selectedAgents.forEach((a) => formData.append('agents', a))
        formData.append('history', JSON.stringify(history))

        const res = await fetch(`${API_BASE}/api/upload/`, {
          method: 'POST',
          body: formData,
        })
        const data = await res.json()
        setAttachedFiles([])

        if (data.type === 'chat') {
          updateLastEntry(entryIdNum, { type: 'chat', message: data.message })
        } else if (data.success) {
          updateLastEntry(entryIdNum, {
            type: 'coding',
            code: data.code || '',
            review: data.review || '',
            tests: data.tests || '',
            duration: 0,
          })
          updateActiveTab(entryIdNum, 'code')
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        updateLastEntry(entryIdNum, { type: 'chat', message: `Upload failed: ${msg}` })
      }
      setLoading(false)
      inputRef.current?.focus()
      return
    }

    if (mode === 'chat') {
      setCurrentStatus('💬 Thinking...')
      try {
        const res = await fetch(`${API_BASE}/api/chat/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: desc, history, model: selectedModel, web_search: webSearchEnabled }),
        })
        const data = await res.json()
        updateLastEntry(entryIdNum, {
          type: 'chat',
          message: res.ok ? data.message : data.error || 'The chat model request failed.',
        })
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        updateLastEntry(entryIdNum, { type: 'chat', message: `Sorry, I couldn't reach the server: ${msg}` })
      }
      setLoading(false)
      inputRef.current?.focus()
      return
    }

    if (mode === 'debug') {
      setCurrentStatus('🔍 Analyzing error...')
      try {
        const res = await fetch(`${API_BASE}/api/debug/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ error: desc, model: selectedModel }),
        })
        const data = await res.json()
        updateLastEntry(entryIdNum, {
          type: 'debug',
          errorType: data.error_type,
          analysis: data.analysis,
          fix: data.fix,
          code: data.code || '',
        })
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        updateLastEntry(entryIdNum, { type: 'chat', message: `Debug endpoint unavailable: ${msg}` })
      }
      setLoading(false)
      inputRef.current?.focus()
      return
    }

    addLog(`[Orchestrator] Starting workflow: "${desc}"`)
    setAgentTask('coder', desc)
    setCurrentStatus('✍ Writing code...')

    try {
      const body: Record<string, unknown> = { prompt: desc, history, ...commonBody }
      if (pendingPlan) {
        body.plan = pendingPlan
        body.plan_approved = true
        setPendingPlan(null)
        setPendingPlanPrompt('')
      }
      const res = await fetch(`${API_BASE}/api/workflow/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (data.type === 'plan') {
        setCurrentStatus('📋 Plan generated')
        setPendingPlan(data.plan)
        setPendingPlanPrompt(desc)
        addLog('[Planner] Implementation plan generated, awaiting approval')
        updateLastEntry(entryIdNum, { type: 'plan', plan: data.plan })
      } else if (data.type === 'research') {
        setCurrentStatus('🔬 Research complete')
        addLog('[Researcher] Deep research complete')
        updateLastEntry(entryIdNum, { type: 'research', research: data.research || data.message || '' })
      } else if (!data.success) {
        setCurrentStatus('❌ Error')
        addLog(`[Orchestrator] Error: ${data.error}`)
        setAgentTask('coder', null)
        updateLastEntry(entryIdNum, {
          type: 'chat',
          message: data.error || 'The agent could not complete this request.',
        })
      } else {
        addLog(`[Coder] Code generated (${data.code.length} chars)`)
        setCurrentStatus('🔍 Reviewing code...')
        addLog('[Coder] Phase 1/3: Code written, starting review...')
        addLog('[Coder] Phase 2/3: Review complete')
        addLog('[Coder] Phase 3/3: Tests generated')
        incrementTasks('coder', 'Code, review, and tests complete')
        setCurrentStatus('✅ Workflow complete')
        addLog(`[Orchestrator] Workflow complete in ${data.duration.toFixed(1)}s`)

        updateLastEntry(entryIdNum, {
          type: 'coding',
          code: data.code,
          review: data.review,
          tests: data.tests,
          duration: data.duration,
        })
        updateActiveTab(entryIdNum, 'code')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      addLog(`[Orchestrator] Connection failed: ${msg}`)
      setAgentTask('coder', null)
    }

    setLoading(false)
    inputRef.current?.focus()
  }

  function startWaveform() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      micStreamRef.current = stream
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 32
      source.connect(analyser)
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      audioContextRef.current = audioCtx
      analyserRef.current = analyser
      dataArrayRef.current = dataArray

      function draw() {
        if (!analyserRef.current || !dataArrayRef.current || !canvasRef.current) return
        analyserRef.current.getByteFrequencyData(dataArrayRef.current)
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        const bars = dataArrayRef.current.length
        const barW = canvas.width / bars
        for (let i = 0; i < bars; i++) {
          const h = (dataArrayRef.current[i] / 255) * canvas.height
          const hue = 200 + (dataArrayRef.current[i] / 255) * 40
          ctx.fillStyle = `hsl(${hue}, 80%, 60%)`
          ctx.fillRect(i * barW + 1, canvas.height - h, barW - 2, Math.max(h, 1))
        }
        animFrameRef.current = requestAnimationFrame(draw)
      }
      draw()
    }).catch(() => {})
  }

  function stopWaveform() {
    cancelAnimationFrame(animFrameRef.current)
    audioContextRef.current?.close()
    micStreamRef.current?.getTracks().forEach((t) => t.stop())
    audioContextRef.current = null
    analyserRef.current = null
    dataArrayRef.current = null
    micStreamRef.current = null
    const canvas = canvasRef.current
    if (canvas) {
      const ctx = canvas.getContext('2d')
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
    }
  }

  const toggleRecording = useCallback(() => {
    if (recordingRef.current) {
      stopWaveform()
      recognitionRef.current?.stop()
      recognitionRef.current = null
      recordingRef.current = false
      setRecording(false)
      const text = transcriptRef.current
      if (text.trim()) {
        setPrompt(text)
        setTimeout(() => sendMessage(), 0)
      }
      return
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      addLog('[System] Speech recognition not supported in this browser.')
      return
    }
    transcriptRef.current = ''
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.onresult = (e: any) => {
      let full = ''
      for (let i = 0; i < e.results.length; i++) {
        full += e.results[i][0].transcript
      }
      transcriptRef.current = full
      setPrompt(full)
    }
    recognition.onerror = (e: any) => {
      addLog(`[System] Speech error: ${e.error}`)
      stopWaveform()
      recordingRef.current = false
      setRecording(false)
    }
    recognition.onend = () => {
      if (recordingRef.current) {
        try { recognition.start() } catch {}
      } else {
        setRecording(false)
      }
    }
    recognition.start()
    recognitionRef.current = recognition
    recordingRef.current = true
    setRecording(true)
    startWaveform()
  }, [addLog])

  function renderAgentResponse(entry: ConversationEntry) {
    const r = entry.result
    if (r.type === 'image') {
      const isSvg = r.mimeType === 'image/svg+xml'
      return (
        <div style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderRadius: '12px 12px 12px 0',
          border: '1px solid var(--border)',
          padding: 12,
          textAlign: 'center',
        }}>
          {isSvg && (
            <div style={{ fontSize: 10, color: 'var(--accent-yellow)', marginBottom: 6, background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: 4, display: 'inline-block' }}>
              ⚠ SVG vector illustration (not a photograph — Gemini Image model quota was exceeded)
            </div>
          )}
          <img src={`data:${r.mimeType};base64,${r.imageData}`} alt="Generated"
            style={{ maxWidth: '100%', maxHeight: 400, borderRadius: 8 }} />
        </div>
      )
    }
    if (r.type === 'plan') {
      return (
        <div style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderRadius: '12px 12px 12px 0',
          border: '1px solid var(--border)',
          padding: '12px 16px',
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            📋 Implementation Plan
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
            {r.plan}
          </div>
        </div>
      )
    }
    if (r.type === 'research') {
      return (
        <div style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderRadius: '12px 12px 12px 0',
          border: '1px solid var(--border)',
          padding: '12px 16px',
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-purple)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            🔬 Deep Research
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
            {r.research}
          </div>
        </div>
      )
    }
    if (r.type === 'chat') {
      // Show pixel loading animation for image placeholder entries
      const isImagePlaceholder = !r.message && entry.prompt.startsWith('🎨')
      return (
        <div style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderRadius: '12px 12px 12px 0',
          border: '1px solid var(--border)',
          padding: isImagePlaceholder ? 0 : '12px 16px',
          fontSize: 13,
          lineHeight: 1.6,
          color: 'var(--text-primary)',
          whiteSpace: 'pre-wrap',
          textAlign: isImagePlaceholder ? 'center' : undefined,
        }}>
          {isImagePlaceholder ? (
            <div style={{ padding: '16px 0' }}>
              <div className="pixel-loading" />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                🎨 Generating image<span style={{ animation: 'pulse 1.2s ease-in-out infinite' }}>...</span>
              </div>
            </div>
          ) : (
            r.message
          )}
        </div>
      )
    }

    if (r.type === 'debug') {
      return (
        <div style={{
          flex: 1,
          background: 'var(--bg-secondary)',
          borderRadius: '12px 12px 12px 0',
          border: '1px solid var(--border)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 12px',
            background: 'var(--accent-red)',
            color: '#fff',
            fontSize: 11,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <span>⚠️</span>
            <span>{r.errorType}</span>
          </div>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-red)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Analysis
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
              {r.analysis}
            </div>
          </div>
          <div style={{ padding: '12px 16px', borderBottom: r.code ? '1px solid var(--border)' : 'none' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-green)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Fix
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
              {r.fix}
            </div>
          </div>
          {r.code && (
            <div>
              <div style={{
                padding: '8px 12px', fontSize: 11, fontWeight: 600,
                color: 'var(--accent-blue)', background: 'var(--bg-tertiary)',
                borderBottom: '1px solid var(--border)',
                textTransform: 'uppercase', letterSpacing: '0.5px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <span>💻 Corrected Code</span>
                <button onClick={() => {
                  navigator.clipboard.writeText(r.code)
                  setCopiedId(`debug-${entry.id}`)
                  setTimeout(() => setCopiedId(null), 1500)
                }} style={{
                  background: copiedId === `debug-${entry.id}` ? 'var(--accent-green)' : 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
                  fontSize: 10, color: copiedId === `debug-${entry.id}` ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }} title="Copy code"
                onMouseEnter={(e) => { if (copiedId !== `debug-${entry.id}`) e.currentTarget.style.background = 'var(--bg-tertiary)' }}
                onMouseLeave={(e) => { if (copiedId !== `debug-${entry.id}`) e.currentTarget.style.background = 'var(--bg-secondary)' }}
                >{copiedId === `debug-${entry.id}` ? '✓ Copied!' : '📋 Copy'}</button>
              </div>
              <pre style={{
                margin: 0, padding: 12, fontSize: 11, lineHeight: 1.5,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                color: 'var(--text-primary)', overflow: 'auto', maxHeight: 300,
                whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                background: '#0d1117',
              }}>
                {r.code}
              </pre>
            </div>
          )}
        </div>
      )
    }

    const coding = r as { type: 'coding'; code: string; review: string; tests: string; duration: number; error?: string }
    return (
      <div style={{
        flex: 1,
        background: 'var(--bg-secondary)',
        borderRadius: '12px 12px 12px 0',
        border: '1px solid var(--border)',
        overflow: 'hidden',
      }}>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
          {(['code', 'review', 'tests'] as const).map((tab) => (
            <button key={tab} onClick={() => updateActiveTab(entry.id, tab)} style={{
              flex: 1, padding: '8px', border: 'none',
              background: activeTab[entry.id] === tab ? 'var(--bg-tertiary)' : 'transparent',
              color: activeTab[entry.id] === tab ? 'var(--accent-blue)' : 'var(--text-muted)',
              fontWeight: activeTab[entry.id] === tab ? 600 : 400,
              fontSize: 11, textTransform: 'capitalize', cursor: 'pointer',
              borderBottom: activeTab[entry.id] === tab ? '2px solid var(--accent-blue)' : '2px solid transparent',
            }}>
              {tab === 'code' ? '💻 Code' : tab === 'review' ? '🔍 Review' : '🧪 Tests'}
            </button>
          ))}
        </div>
        <pre style={{
          margin: 0, padding: 12, fontSize: 11, lineHeight: 1.5,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          color: 'var(--text-primary)', overflow: 'auto', maxHeight: 300,
          whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          background: '#0d1117',
        }}>
          {coding.error || (activeTab[entry.id] === 'code' ? coding.code : activeTab[entry.id] === 'review' ? coding.review : coding.tests)}
        </pre>
        {!coding.error && (
          <div style={{
            padding: '4px 12px', fontSize: 10, color: 'var(--text-muted)',
            borderTop: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                fontSize: 10,
                background: 'var(--accent-blue)',
                color: '#fff',
                borderRadius: 4,
                padding: '1px 6px',
                textTransform: 'uppercase',
              }}>
                {_detectLanguage(entry.prompt)}
              </span>
              <button onClick={() => {
                const text = coding.error || (activeTab[entry.id] === 'code' ? coding.code : activeTab[entry.id] === 'review' ? coding.review : coding.tests)
                navigator.clipboard.writeText(text)
                setCopiedId(`coding-${entry.id}`)
                setTimeout(() => setCopiedId(null), 1500)
              }} style={{
                background: copiedId === `coding-${entry.id}` ? 'var(--accent-green)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border)',
                borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
                fontSize: 10, color: copiedId === `coding-${entry.id}` ? '#fff' : 'var(--text-muted)',
                transition: 'all 0.15s',
              }} title="Copy to clipboard"
              onMouseEnter={(e) => { if (copiedId !== `coding-${entry.id}`) e.currentTarget.style.background = 'var(--bg-secondary)' }}
              onMouseLeave={(e) => { if (copiedId !== `coding-${entry.id}`) e.currentTarget.style.background = 'var(--bg-tertiary)' }}
              >{copiedId === `coding-${entry.id}` ? '✓ Copied!' : '📋 Copy'}</button>
            </span>
            <span>{coding.duration.toFixed(2)}s</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 108px)', gap: 12 }}>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes pixel-load {
          0% { background-position: 0 0; }
          100% { background-position: 64px 64px; }
        }
        .pixel-loading {
          width: 200px; height: 200px; margin: 12px auto;
          background:
            linear-gradient(45deg, #333 25%, transparent 25%) 0 0 / 16px 16px,
            linear-gradient(-45deg, #333 25%, transparent 25%) 0 0 / 16px 16px,
            linear-gradient(45deg, transparent 75%, #333 75%) 0 0 / 16px 16px,
            linear-gradient(-45deg, transparent 75%, #333 75%) 0 0 / 16px 16px;
          background-color: #555;
          animation: pixel-load 0.8s linear infinite;
          border-radius: 8px;
          image-rendering: pixelated;
        }
      `}</style>
      {sidebarOpen && (
        <div style={{
          width: 240, flexShrink: 0,
          display: 'flex', flexDirection: 'column',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)',
          overflow: 'hidden',
        }}>
          <div style={{ padding: 12, borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button onClick={newSession} style={{
              width: '100%', padding: '8px 12px',
              borderRadius: 'var(--radius)',
              border: '1px dashed var(--border)',
              background: 'transparent',
              color: 'var(--accent-blue)',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>+</span> New Chat
            </button>
            <button onClick={() => setShowArchived((o) => !o)} style={{
              width: '100%', padding: '6px 12px',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              background: showArchived ? 'var(--bg-tertiary)' : 'transparent',
              color: 'var(--text-muted)',
              fontSize: 11, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>📁</span> Archived ({archivedSessions.length})
            </button>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: 4 }}>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => switchSession(s.id)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius)',
                  cursor: 'pointer',
                  marginBottom: 2,
                  background: s.id === activeSessionId ? 'var(--bg-tertiary)' : 'transparent',
                  border: s.id === activeSessionId ? '1px solid var(--accent-blue)' : '1px solid transparent',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{
                    fontSize: 12, fontWeight: s.id === activeSessionId ? 600 : 400,
                    color: 'var(--text-primary)', marginBottom: 2,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {s.name}
                  </div>
                  <div style={{
                    fontSize: 10, color: 'var(--text-muted)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {sessionPreview(s)}
                  </div>
                </div>
                {sessions.length > 1 && (
                  <button
                    onClick={(e) => deleteSession(s.id, e)}
                    style={{
                      background: 'none', border: 'none',
                      color: 'var(--text-muted)', cursor: 'pointer',
                      fontSize: 14, padding: '2px 4px', borderRadius: 4,
                      lineHeight: 1, flexShrink: 0, opacity: 0,
                    }}
                    className="session-delete-btn"
                    title="Archive session"
                  >×</button>
                )}
              </div>
            ))}
            {showArchived && archivedSessions.length > 0 && (
              <>
                <div style={{
                  padding: '8px 12px 4px', fontSize: 10, fontWeight: 600,
                  color: 'var(--text-muted)', textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}>Archived</div>
                {archivedSessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => restoreSession(s)}
                    style={{
                      padding: '10px 12px',
borderRadius: 50,
                      cursor: 'pointer',
                      marginBottom: 2,
                      opacity: 0.6,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{
                        fontSize: 12, color: 'var(--text-muted)', marginBottom: 2,
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {s.name}
                      </div>
                      <div style={{
                        fontSize: 10, color: 'var(--text-muted)',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {sessionPreview(s)}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setArchivedSessions((prev) => prev.filter((a) => a.id !== s.id)) }}
                      style={{
                        background: 'none', border: 'none',
                        color: 'var(--text-muted)', cursor: 'pointer',
                        fontSize: 12, padding: '2px 4px', borderRadius: 4,
                        lineHeight: 1, flexShrink: 0,
                      }}
                      title="Delete permanently"
                    >🗑</button>
                  </div>
                ))}
              </>
            )}
          </div>
          <style>{`
            .session-delete-btn { opacity: 0 !important; transition: opacity 0.15s; }
            div:hover > .session-delete-btn { opacity: 0.6 !important; }
            .session-delete-btn:hover { opacity: 1 !important; }
          `}</style>
        </div>
      )}

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexShrink: 0 }}>
          <button onClick={() => setSidebarOpen((o) => !o)} style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', padding: '4px 8px',
            cursor: 'pointer', fontSize: 14, color: 'var(--text-secondary)',
          }}>
            {sidebarOpen ? '☰' : '☰'}
          </button>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
            {activeSession?.name || 'Multi-Agent System'}
          </h2>
        </div>

        <div style={{
          flex: 1, overflow: 'auto', marginBottom: 10,
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          {conversation.length === 0 && (
            <div style={{
              textAlign: 'center', padding: '60px 20px',
              color: 'var(--text-muted)', fontSize: 13,
            }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>💬</div>
              <div>Chat with the multi-agent coding assistant.</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>Say hello, ask about features, or request code.</div>
            </div>
          )}
          {conversation.map((entry) => (
            <div key={entry.id}>
              <div style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                marginBottom: 6,
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: 'var(--accent-blue)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, color: '#fff', flexShrink: 0,
                }}>U</div>
                <div style={{
                  background: 'var(--bg-tertiary)',
                  borderRadius: '0 10px 10px 10px',
                  padding: '8px 12px',
                  fontSize: 13,
                  color: 'var(--text-primary)',
                  maxWidth: '80%',
                }}>
                  {entry.prompt}
                </div>
              </div>
              <div style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                marginBottom: 6,
              }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: 'var(--accent-green)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, color: '#fff', flexShrink: 0,
                }}>A</div>
                {renderAgentResponse(entry)}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <div style={{
          flexShrink: 0,
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 10,
        }}>
          {/* Plan approval bar */}
          {pendingPlan && (
            <div style={{
              marginBottom: 8, padding: '8px 12px',
              background: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--accent-cyan)',
              display: 'flex', alignItems: 'center', gap: 8,
              fontSize: 11,
            }}>
              <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>📋 Plan ready for: {pendingPlanPrompt.slice(0, 40)}</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                <button onClick={() => { setPendingPlan(null); setPendingPlanPrompt(''); setPrompt('') }}
                  style={{ padding: '4px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)',
                    background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 10 }}>
                  ✕ Reject
                </button>
                <button onClick={() => { executePendingPlan() }}
                  style={{ padding: '4px 10px', borderRadius: 'var(--radius)', border: 'none',
                    background: 'var(--accent-green)', color: '#fff', cursor: 'pointer', fontSize: 10, fontWeight: 600 }}>
                  ✓ Execute Plan
                </button>
              </div>
            </div>
          )}

          {/* Control bar */}
          <div style={{
            marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
          }}>
            {/* Model selector */}
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{
                padding: '4px 6px 4px 6px', borderRadius: 'var(--radius)',
                border: '1px solid var(--border)', background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)', fontSize: 10, cursor: 'pointer', outline: 'none', width: 260,
              }}>
                {(() => {
                  const models = availableModels.length > 0 ? availableModels : [
                    {id: 'gemini-3.1-flash-lite', name: 'Gemini 3.1 Flash Lite', group: '⚡ General', daily_limit: 1500},
                    {id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', group: '⚡ General', daily_limit: 1500},
                    {id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', group: '⚡ General', daily_limit: 1500},
                    {id: 'groq/llama-3.1-8b-instant', name: 'Groq Llama 3.1 8B', group: '⚡ General', daily_limit: 14400},
                    {id: 'groq/llama-3.3-70b-versatile', name: 'Groq Llama 3.3 70B', group: '⚡ General', daily_limit: 14400},
                    {id: 'hf/meta-llama/Llama-3.1-8B-Instruct', name: 'HF Llama 3.1 8B', group: '⚡ General', daily_limit: 600},
                    {id: 'hf/black-forest-labs/FLUX.1-schnell', name: 'HF FLUX.1 Schnell', group: '🎨 Image', daily_limit: 100},
                  ]
                  const groups: Record<string, typeof models> = {}
                  for (const m of models) {
                    const g = (m as any).group || 'Models'
                    if (!groups[g]) groups[g] = []
                    groups[g].push(m)
                  }
                  return Object.entries(groups).map(([groupName, items]) => (
                    <optgroup key={groupName} label={groupName}>
                      {items.map((m: any) => {
                        const u = modelUsage[m.id]
                        const remaining = u && u.limit > 0 ? u.remaining : null
                        const used = u?.used ?? null
                        const limit = u?.limit ?? null
                        const pct = u?.percent ?? null
                        const indicator = u?.source === 'api' ? '✓' : '~'
                        const label = remaining !== null
                          ? `${m.name}  ${indicator} ${used}/${limit}  (${pct}%)`
                          : m.name
                        return (
                          <option key={m.id} value={m.id}>{label}</option>
                        )
                      })}
                    </optgroup>
                  ))
                })()}
              </select>
            </div>

            {/* Coder toggle */}
            {['coder'].map((role) => (
              <button key={role} onClick={() => {
                setSelectedAgents((prev) =>
                  prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
                )
              }} style={{
                padding: '3px 8px', borderRadius: 'var(--radius)',
                border: `1px solid ${selectedAgents.includes(role) ? AGENT_COLORS[role] : 'var(--border)'}`,
                background: selectedAgents.includes(role) ? `${AGENT_COLORS[role]}22` : 'transparent',
                color: selectedAgents.includes(role) ? AGENT_COLORS[role] : 'var(--text-muted)',
                fontSize: 10, cursor: 'pointer', fontWeight: selectedAgents.includes(role) ? 600 : 400,
              }}>
                💻 {role}
              </button>
            ))}

            {/* Web search toggle */}
            <button onClick={() => setWebSearchEnabled((o) => !o)} title="Web search" style={{
              padding: '3px 8px', borderRadius: 'var(--radius)',
              border: `1px solid ${webSearchEnabled ? 'var(--accent-blue)' : 'var(--border)'}`,
              background: webSearchEnabled ? 'rgba(59,130,246,0.15)' : 'transparent',
              color: webSearchEnabled ? 'var(--accent-blue)' : 'var(--text-muted)',
              fontSize: 10, cursor: 'pointer', fontWeight: webSearchEnabled ? 600 : 400,
            }}>
              🌐 {webSearchEnabled ? 'Web' : 'No web'}
            </button>

            {/* Research mode toggle */}
            <button onClick={() => setResearchMode((o) => !o)} title="Deep research" style={{
              padding: '3px 8px', borderRadius: 'var(--radius)',
              border: `1px solid ${researchMode ? 'var(--accent-purple)' : 'var(--border)'}`,
              background: researchMode ? 'rgba(168,85,247,0.15)' : 'transparent',
              color: researchMode ? 'var(--accent-purple)' : 'var(--text-muted)',
              fontSize: 10, cursor: 'pointer', fontWeight: researchMode ? 600 : 400,
            }}>
              🔬 {researchMode ? 'Research' : 'No research'}
            </button>

            {/* Planning toggle */}
            <button onClick={() => setPlanningMode((o) => !o)} title="Plan before coding" style={{
              padding: '3px 8px', borderRadius: 'var(--radius)',
              border: `1px solid ${planningMode ? 'var(--accent-cyan)' : 'var(--border)'}`,
              background: planningMode ? 'rgba(6,182,212,0.15)' : 'transparent',
              color: planningMode ? 'var(--accent-cyan)' : 'var(--text-muted)',
              fontSize: 10, cursor: 'pointer', fontWeight: planningMode ? 600 : 400,
            }}>
              📋 {planningMode ? 'Plan' : 'No plan'}
            </button>

            {/* Image gen button */}
            <button onClick={() => {
              setPrompt('/image ')
              inputRef.current?.focus()
            }} title="Generate image (type /image <prompt>)" style={{
              padding: '3px 8px', borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: 10, cursor: 'pointer',
            }}>
              🎨 Image
            </button>

            {/* Clear button */}
            <button onClick={() => setPrompt('')} style={{
              padding: '3px 8px', borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: 10, cursor: 'pointer', marginLeft: 'auto',
            }}>
              ✕ Clear
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {loading && currentStatus && (
                <div style={{
                  fontSize: 11, color: 'var(--text-muted)', padding: '4px 0',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <span style={{ display: 'inline-block', width: 8, textAlign: 'center' }}>
                    <span style={{ animation: 'pulse 1.2s ease-in-out infinite' }}>●</span>
                  </span>
                  {currentStatus}
                  <span style={{ animation: 'pulse 1.2s ease-in-out infinite', marginLeft: 2 }}>
                    ...
                  </span>
                </div>
              )}
              {attachedFiles.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {attachedFiles.map((f, i) => (
                    <span key={i} onClick={() => setPreviewFile(f)} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 8px', borderRadius: 'var(--radius)',
                      background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
                      fontSize: 10, color: 'var(--text-muted)', cursor: 'pointer',
                    }}>
                      {f.type.startsWith('image/') ? '🖼' : f.type.startsWith('video/') ? '🎬' : f.type.startsWith('audio/') ? '🎵' : '📎'}
                      {' '}{f.name.length > 20 ? f.name.slice(0, 18) + '..' : f.name}
                      <button onClick={(e) => { e.stopPropagation(); setAttachedFiles((prev) => prev.filter((_, j) => j !== i)) }} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', fontSize: 12, padding: 0, lineHeight: 1,
                      }}>×</button>
                    </span>
                  ))}
                </div>
              )}
              <div style={{ position: 'relative' }}>
                <textarea
                ref={inputRef}
                value={prompt}
                onChange={(e) => { setPrompt(e.target.value); autoResize(e.target) }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !loading) {
                    e.preventDefault()
                    sendMessage()
                  }
                  setTimeout(() => autoResize(e.target as HTMLTextAreaElement), 0)
                }}
                placeholder="Chat with the agent..."
                disabled={loading}
                rows={1}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  padding: '8px 60px 8px 40px', borderRadius: 24,
                  border: '1px solid var(--border)',
                  background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
                  fontSize: 14, outline: 'none', resize: 'none', overflow: 'hidden',
                  fontFamily: 'inherit', lineHeight: 1.5,
                  opacity: loading ? 0.5 : 1,
                }}
              />
              <div ref={addMenuRef} style={{ position: 'absolute', top: '50%', transform: 'translateY(calc(-50% - 3px))', left: 0 }}>
                <button onClick={() => setShowAddMenu((o) => !o)} style={{
                  padding: '10px 16px', borderRadius: 'var(--radius)',
                  border: 'none',
                  background: attachedFiles.length > 0 ? 'var(--accent-blue)' : 'transparent',
                  color: attachedFiles.length > 0 ? '#fff' : 'var(--text-muted)',
                  fontSize: 20, cursor: 'pointer', whiteSpace: 'nowrap', fontWeight: 600,
                  lineHeight: 1.4,
                }} title="Add">
                  +
                </button>
                {showAddMenu && (
                  <div style={{
                    position: 'absolute', top: '100%', left: 0, marginTop: 4,
                    background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)', padding: 4, minWidth: 160,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)', zIndex: 100,
                  }}>
                    <button onClick={() => { fileInputRef.current?.click(); setShowAddMenu(false) }} style={{
                      display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                      padding: '8px 12px', borderRadius: 'var(--radius)',
                      border: 'none', background: 'transparent', color: 'var(--text-primary)',
                      fontSize: 12, cursor: 'pointer', textAlign: 'left',
                    }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <span>📎</span> Attach files
                    </button>
                    <button onClick={async () => {
                      setShowAddMenu(false)
                      try {
                        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                        setCameraStream(stream)
                        setCameraActive(true)
                        setTimeout(() => {
                          if (videoRef.current) videoRef.current.srcObject = stream
                        }, 100)
                      } catch {
                        addLog('[System] Camera access denied or unavailable')
                      }
                    }} style={{
                      display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                      padding: '8px 12px', borderRadius: 'var(--radius)',
                      border: 'none', background: 'transparent', color: 'var(--text-primary)',
                      fontSize: 12, cursor: 'pointer', textAlign: 'left',
                    }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <span>📷</span> Take Photo
                    </button>
                    <button onClick={async () => {
                      setShowAddMenu(false)
                      try {
                        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
                        const track = stream.getVideoTracks()[0]
                        const imgCapture = new ImageCapture(track)
                        const bitmap = await imgCapture.grabFrame()
                        track.stop()
                        stream.getTracks().forEach((t) => t.stop())
                        const canvas = document.createElement('canvas')
                        canvas.width = bitmap.width
                        canvas.height = bitmap.height
                        canvas.getContext('2d')!.drawImage(bitmap, 0, 0)
                        setSnipMode({ dataUrl: canvas.toDataURL('image/png') })
                        setSnipRect(null)
                        setSnipStart(null)
                      } catch {
                        addLog('[System] Screenshot cancelled')
                      }
                    }} style={{
                      display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                      padding: '8px 12px', borderRadius: 'var(--radius)',
                      border: 'none', background: 'transparent', color: 'var(--text-primary)',
                      fontSize: 12, cursor: 'pointer', textAlign: 'left',
                    }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <span>🖥️</span> Take Screenshot
                    </button>
                  </div>
                )}
              </div>
              <canvas ref={canvasRef} width={48} height={24} style={{
                position: 'absolute', top: '50%', right: 80, transform: 'translateY(calc(-50% - 2px))',
                width: 48, height: 24, borderRadius: 4,
                display: recording ? 'block' : 'none', pointerEvents: 'none',
              }} />
              <button onClick={toggleRecording} style={{
                position: 'absolute', top: '50%', right: 44, transform: 'translateY(calc(-50% - 2px))',
                width: 28, height: 28, padding: 0, borderRadius: '50%',
                border: 'none', background: recording ? '#e53e3e' : 'transparent',
                color: recording ? '#fff' : 'var(--text-muted)',
                fontSize: 16, cursor: 'pointer', lineHeight: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'background 0.2s',
              }} title={recording ? 'Stop recording' : 'Start dictation'}>
                🎤
              </button>
              <button onClick={sendMessage} disabled={loading} style={{
                position: 'absolute', top: '50%', right: 12, transform: 'translateY(calc(-50% - 2px))',
                width: 28, height: 28, padding: 0, borderRadius: '50%',
                border: 'none', background: loading ? 'var(--text-muted)' : 'var(--accent-blue)',
                color: '#fff', fontWeight: 600, fontSize: 14,
                cursor: loading ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
                lineHeight: 1.4,
              }}>
                ↑
              </button>
              </div>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.ppt,.pptx,.txt,.md,.json,.xml,.yaml,.yml,.toml,.ini,.cfg,.log,.py,.js,.ts,.jsx,.tsx,.html,.css,.scss,.sql,.sh,.bat,.ps1,.zip,.tar,.gz"
              onChange={(e) => {
                const files = Array.from(e.target.files || [])
                setAttachedFiles((prev) => [...prev, ...files])
                e.target.value = ''
              }}
              style={{ display: 'none' }}
            />
          </div>
        </div>
      </div>

      {previewFile && (
        <div onClick={() => setPreviewFile(null)} style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0,0,0,0.85)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer',
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            maxWidth: '90vw', maxHeight: '90vh',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden', display: 'flex', flexDirection: 'column',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px', borderBottom: '1px solid var(--border)',
            }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {previewFile.name}
              </span>
              <button onClick={() => setPreviewFile(null)} style={{
                background: 'none', border: 'none', color: 'var(--text-muted)',
                fontSize: 16, cursor: 'pointer', padding: '0 4px',
              }}>×</button>
            </div>
            <div style={{ padding: 16, overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {previewFile.type.startsWith('image/') ? (
                <img src={URL.createObjectURL(previewFile)} alt={previewFile.name}
                  style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 'var(--radius)' }} />
              ) : previewFile.type.startsWith('video/') ? (
                <video src={URL.createObjectURL(previewFile)} controls style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 'var(--radius)' }} />
              ) : (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{previewFile.name}</div>
                  <div style={{ fontSize: 11 }}>{(previewFile.size / 1024).toFixed(1)} KB</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {snipMode && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: '#000',
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{
            flex: 1, position: 'relative', overflow: 'hidden',
            cursor: snipStart ? 'crosshair' : 'crosshair',
          }}
            onMouseDown={(e) => {
              const rect = e.currentTarget.getBoundingClientRect()
              setSnipStart({ x: e.clientX - rect.left, y: e.clientY - rect.top })
            }}
            onMouseMove={(e) => {
              if (!snipStart) return
              const rect = e.currentTarget.getBoundingClientRect()
              const x = e.clientX - rect.left
              const y = e.clientY - rect.top
              setSnipRect({
                x: Math.min(snipStart.x, x),
                y: Math.min(snipStart.y, y),
                w: Math.abs(x - snipStart.x),
                h: Math.abs(y - snipStart.y),
              })
            }}
            onMouseUp={() => setSnipStart(null)}
            onMouseLeave={() => setSnipStart(null)}
          >
            <img ref={snipImgRef} src={snipMode.dataUrl} alt="screenshot"
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />
            <div style={{
              position: 'absolute', inset: 0,
              background: 'rgba(0,0,0,0.4)',
              pointerEvents: 'none',
            }} />
            {snipRect && snipRect.w > 0 && snipRect.h > 0 && (
              <div style={{
                position: 'absolute',
                left: snipRect.x, top: snipRect.y,
                width: snipRect.w, height: snipRect.h,
                border: '2px solid #fff',
                background: 'transparent',
                boxShadow: '0 0 0 9999px rgba(0,0,0,0.4)',
                pointerEvents: 'none',
              }} />
            )}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
            padding: 12, background: '#111',
          }}>
            <button onClick={() => { setSnipMode(null); setSnipRect(null); setSnipStart(null) }} style={{
              padding: '8px 20px', borderRadius: 'var(--radius)',
              border: '1px solid #444', background: 'transparent',
              color: '#fff', fontSize: 13, cursor: 'pointer',
            }}>
              ✕ Cancel
            </button>
            <button onClick={() => {
              if (snipRect && snipRect.w >= 10 && snipRect.h >= 10) {
                const img = snipImgRef.current
                if (!img) return
                const scaleX = img.naturalWidth / img.offsetWidth
                const scaleY = img.naturalHeight / img.offsetHeight
                const c = document.createElement('canvas')
                c.width = snipRect.w * scaleX
                c.height = snipRect.h * scaleY
                const ctx = c.getContext('2d')!
                ctx.drawImage(img, snipRect.x * scaleX, snipRect.y * scaleY, c.width, c.height, 0, 0, c.width, c.height)
                c.toBlob((blob) => {
                  if (blob) {
                    const file = new File([blob], `snip-${Date.now()}.png`, { type: 'image/png' })
                    setAttachedFiles((prev) => [...prev, file])
                  }
                  setSnipMode(null)
                  setSnipRect(null)
                  setSnipStart(null)
                })
              }
            }} style={{
              padding: '8px 20px', borderRadius: 'var(--radius)',
              border: 'none', background: 'var(--accent-blue)',
              color: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 600,
            }}>
              ✂️ Add Selection
            </button>
          </div>
        </div>
      )}

      {cameraActive && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0,0,0,0.85)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        }}>
          <video ref={videoRef} autoPlay playsInline style={{
            maxWidth: '100%', maxHeight: '80vh', borderRadius: 'var(--radius-lg)',
          }} />
          <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
            <button onClick={() => {
              setCameraActive(false)
              if (cameraStream) {
                cameraStream.getTracks().forEach((t) => t.stop())
                setCameraStream(null)
              }
            }} style={{
              padding: '8px 20px', borderRadius: 'var(--radius)',
              border: '1px solid var(--border)', background: 'var(--bg-secondary)',
              color: 'var(--text-primary)', fontSize: 13, cursor: 'pointer',
            }}>
              ✕ Cancel
            </button>
            <button onClick={() => {
              const video = videoRef.current
              if (!video) return
              const canvas = document.createElement('canvas')
              canvas.width = video.videoWidth
              canvas.height = video.videoHeight
              const ctx = canvas.getContext('2d')!
              ctx.drawImage(video, 0, 0)
              canvas.toBlob((blob) => {
                if (blob) {
                  const file = new File([blob], `photo-${Date.now()}.png`, { type: 'image/png' })
                  setAttachedFiles((prev) => [...prev, file])
                }
                setCameraActive(false)
                if (cameraStream) {
                  cameraStream.getTracks().forEach((t) => t.stop())
                  setCameraStream(null)
                }
              }, 'image/png')
            }} style={{
              padding: '8px 20px', borderRadius: 'var(--radius)',
              border: 'none', background: 'var(--accent-blue)',
              color: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 600,
            }}>
              📸 Capture
            </button>
          </div>
        </div>
      )}
    </div>
  )
}