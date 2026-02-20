import { useState, useEffect, useCallback, useRef } from 'react'
import { Marked } from 'marked'
import hljs from 'highlight.js'
import type { Conversation, Message, Model, SystemPrompt, FileAttachment, ChatOpts } from './types'
import Sidebar from './components/Sidebar'
import Toolbar from './components/Toolbar'
import ChatView from './components/ChatView'
import InputBar from './components/InputBar'
import SettingsSheet from './components/SettingsSheet'

// ── Regex to match file-content blocks injected by attachment system ──
const FILE_BLOCK_RE = /<div class="yaog-file-content"[^>]*>[\s\S]*?<\/div>/g
const FILE_NAME_RE = /data-filename="([^"]+)"/g

// ── Markdown renderer ──
const marked = new Marked({
  gfm: true,
  breaks: false,
  renderer: {
    code({ text, lang }: { text: string; lang?: string }) {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted = hljs.highlight(text, { language }).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    },
  },
})

function renderMarkdown(content: string): string {
  try { return marked.parse(content) as string }
  catch { return content.replace(/</g, '&lt;').replace(/>/g, '&gt;') }
}

/** Strip file-content blocks → { text, filenames } */
function stripFileContent(content: string): { text: string; filenames: string[] } {
  const filenames: string[] = []
  let match: RegExpExecArray | null
  const re = new RegExp(FILE_NAME_RE.source, 'g')
  while ((match = re.exec(content)) !== null) filenames.push(match[1])
  const text = content.replace(FILE_BLOCK_RE, '').trim()
  return { text, filenames }
}

/** Build HTML badges for attached files. */
function attachmentBadgesHtml(filenames: string[]): string {
  if (filenames.length === 0) return ''
  const badges = filenames.map(n => `<span class="yaog-attachment-badge">📎 ${n.replace(/</g, '&lt;')}</span>`).join('')
  return `<div class="yaog-attachments-row">${badges}</div>`
}

/** Strip markdown to plain text */
function stripMarkdown(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, m => m.replace(/```\w*\n?/g, '').replace(/```/g, ''))
    .replace(/`([^`]+)`/g, '$1')
    .replace(/#{1,6}\s+/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1').replace(/_([^_]+)_/g, '$1')
    .replace(/~~([^~]+)~~/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '• ').replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^>\s+/gm, '').replace(/---+/g, '').replace(/\n{3,}/g, '\n\n')
    .trim()
}

// ── Display message type ──
export interface DisplayMessage {
  index: number
  role: 'user' | 'assistant' | 'system'
  html: string
  raw: string       // user-typed text only (file content stripped)
  fullRaw: string   // FULL raw content including file blocks
  model: string
}

export default function App() {
  // ── State ──
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [prompts, setPrompts] = useState<SystemPrompt[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [temperature, setTemperature] = useState(1.0)
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null)
  const [useMarkdown, setUseMarkdown] = useState(true)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [useReasoning, setUseReasoning] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const [streamModel, setStreamModel] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<string>('general')
  const [tokenCount, setTokenCount] = useState(0)
  const [stagedFiles, setStagedFiles] = useState<FileAttachment[]>([])
  const [error, setError] = useState<string | null>(null)
  const [apiKeySet, setApiKeySet] = useState(false)
  const [fontSettings, setFontSettings] = useState({
    chat_font_size: 16.5, chat_font_family: 'Literata',
    ui_font_size: 13, ui_font_family: 'DM Sans',
    mono_font_family: 'JetBrains Mono', mono_font_size: 14,
  })

  const streamContentRef = useRef('')

  // ── Apply font settings as CSS custom properties ──
  const applyFontSettings = useCallback((s: typeof fontSettings) => {
    const root = document.documentElement
    root.style.setProperty('--font-chat', `'${s.chat_font_family}', Georgia, serif`)
    root.style.setProperty('--font-ui', `'${s.ui_font_family}', system-ui, sans-serif`)
    root.style.setProperty('--font-mono', `'${s.mono_font_family}', Consolas, monospace`)
    root.style.setProperty('--size-chat', `${s.chat_font_size}px`)
    root.style.setProperty('--size-ui', `${s.ui_font_size}px`)
    root.style.setProperty('--size-mono', `${s.mono_font_size}px`)
    for (const family of [s.chat_font_family, s.ui_font_family, s.mono_font_family]) {
      const id = `gf-${family.replace(/\s+/g, '-').toLowerCase()}`
      if (!document.getElementById(id)) {
        const link = document.createElement('link'); link.id = id; link.rel = 'stylesheet'
        link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@400;500;600;700&display=swap`
        document.head.appendChild(link)
      }
    }
  }, [])

  // ── Init ──
  useEffect(() => {
    async function init() {
      const [convs, mdls, prms, settings] = await Promise.all([
        window.api.convList(), window.api.modelsList(), window.api.promptsList(), window.api.settingsGet(),
      ])
      setConversations(convs); setModels(mdls); setPrompts(prms); setApiKeySet(settings.apiKeySet)
      if (mdls.length > 0) setSelectedModel(mdls[0].id)
      const fs = {
        chat_font_size: settings.chat_font_size ?? 16.5, chat_font_family: settings.chat_font_family ?? 'Literata',
        ui_font_size: settings.ui_font_size ?? 13, ui_font_family: settings.ui_font_family ?? 'DM Sans',
        mono_font_family: settings.mono_font_family ?? 'JetBrains Mono', mono_font_size: settings.mono_font_size ?? 14,
      }
      setFontSettings(fs); applyFontSettings(fs)
    }
    init()
  }, [applyFontSettings])

  // ── Stream events ──
  useEffect(() => {
    window.api.onStreamStart((_index: number, model: string) => {
      setIsStreaming(true); setStreamContent(''); setStreamModel(model); streamContentRef.current = ''
    })
    window.api.onStreamToken((text: string) => { streamContentRef.current += text; setStreamContent(streamContentRef.current) })
    window.api.onStreamDone(async () => {
      setIsStreaming(false); setStreamContent(''); streamContentRef.current = ''
      const msgs = await window.api.chatGetMessages(); setMessages(renderMessages(msgs))
      setTokenCount(await window.api.chatTokenCount())
    })
    window.api.onStreamError((msg: string) => { setIsStreaming(false); setStreamContent(''); streamContentRef.current = ''; setError(msg) })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ──
  const renderMessages = useCallback((msgs: Message[]): DisplayMessage[] => {
    return msgs.filter(m => m.role !== 'system').map(m => {
      const realIndex = msgs.indexOf(m)
      const { text, filenames } = stripFileContent(m.content)
      const badges = attachmentBadgesHtml(filenames)
      const bodyHtml = useMarkdown
        ? renderMarkdown(text)
        : text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
      return {
        index: realIndex, role: m.role,
        html: badges + bodyHtml,
        raw: text,              // clean text only
        fullRaw: m.content,     // FULL content with file blocks
        model: m.model_used || 'AI',
      }
    })
  }, [useMarkdown])

  const chatOpts = useCallback((): ChatOpts => ({ webSearch: useWebSearch, reasoning: useReasoning }), [useWebSearch, useReasoning])

  // ── Actions ──
  const loadConversation = useCallback(async (id: number) => {
    const msgs = await window.api.convLoad(id); setCurrentConvId(id); setMessages(renderMessages(msgs))
    setTokenCount(await window.api.chatTokenCount()); setSidebarOpen(false)
  }, [renderMessages])

  const newChat = useCallback(async () => {
    await window.api.convNew(); setCurrentConvId(null); setMessages([]); setTokenCount(0); setSidebarOpen(false)
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming || (!text.trim() && stagedFiles.length === 0)) return
    const fileNames = stagedFiles.map(f => f.name)
    const badges = attachmentBadgesHtml(fileNames)
    let fullText = text
    for (const f of stagedFiles) fullText += `\n<div class="yaog-file-content" data-filename="${f.name}">\n--- START OF FILE: ${f.name} ---\n${f.content}\n--- END OF FILE: ${f.name} ---\n</div>`
    setStagedFiles([]); setError(null)
    const userHtml = useMarkdown ? renderMarkdown(text) : text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
    setMessages(prev => [...prev, {
      index: prev.length > 0 ? prev[prev.length - 1].index + 1 : 0,
      role: 'user' as const, html: badges + userHtml, raw: text, fullRaw: fullText, model: '',
    }])
    const result = await window.api.chatSend(fullText, selectedModel, temperature, selectedPrompt, chatOpts())
    if (result?.conversations) { setConversations(result.conversations); if (!currentConvId && result.conversations.length > 0) setCurrentConvId(result.conversations[0].id) }
  }, [isStreaming, stagedFiles, selectedModel, temperature, selectedPrompt, chatOpts, useMarkdown, currentConvId])

  const stopGeneration = useCallback(async () => { await window.api.chatStop() }, [])

  const editMessage = useCallback(async (index: number, content: string) => {
    setError(null)
    const result = await window.api.chatEdit(index, content, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    setMessages(renderMessages(await window.api.chatGetMessages()))
  }, [selectedModel, temperature, chatOpts, renderMessages])

  const regenerateMessage = useCallback(async (index: number) => {
    setError(null)
    const result = await window.api.chatRegenerate(index, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    setMessages(renderMessages(await window.api.chatGetMessages()))
  }, [selectedModel, temperature, chatOpts, renderMessages])

  const deleteMessage = useCallback(async (index: number) => {
    const result = await window.api.chatDeleteMsg(index)
    if (result) { setMessages(renderMessages(result.messages)); setTokenCount(result.tokenCount) }
  }, [renderMessages])

  const deleteConversation = useCallback(async (id: number) => {
    await window.api.convDelete(id); setConversations(prev => prev.filter(c => c.id !== id))
    if (currentConvId === id) { setCurrentConvId(null); setMessages([]); setTokenCount(0) }
  }, [currentConvId])

  const renameConversation = useCallback(async (id: number, title: string) => {
    await window.api.convRename(id, title); setConversations(prev => prev.map(c => c.id === id ? { ...c, title } : c))
  }, [])

  const attachFiles = useCallback(async () => {
    const files = await window.api.dialogOpenFiles()
    if (files.length > 0) setStagedFiles(prev => [...prev, ...files])
  }, [])

  const removeStagedFile = useCallback((name: string) => { setStagedFiles(prev => prev.filter(f => f.name !== name)) }, [])

  // ── Conversation-level copy ──
  const copyConversation = useCallback(async (mode: 'text' | 'markdown' | 'full') => {
    // For 'full' mode, get messages WITH file content blocks from backend
    const msgs = mode === 'full'
      ? await window.api.chatGetFullMessages()
      : await window.api.chatGetMessages()

    const parts: string[] = []
    for (const m of msgs) {
      if (m.role === 'system') { parts.push(`[System Prompt]\n${m.content}`); continue }
      const label = m.role === 'user' ? 'You' : (m.model_used || 'AI')

      if (mode === 'full') {
        // Include everything as-is
        parts.push(`[${label}]\n${m.content}`)
      } else if (mode === 'text') {
        // Strip file blocks AND markdown
        const { text } = stripFileContent(m.content)
        parts.push(`[${label}]\n${stripMarkdown(text)}`)
      } else {
        // 'markdown' — strip file blocks, keep markdown
        const { text } = stripFileContent(m.content)
        parts.push(`[${label}]\n${text}`)
      }
    }

    const result = parts.join('\n\n---\n\n')
    await window.api.clipboardWrite(result)
  }, [])

  // Re-render on markdown toggle
  useEffect(() => {
    async function refresh() { const msgs = await window.api.chatGetMessages(); if (msgs.length > 0) setMessages(renderMessages(msgs)) }
    refresh()
  }, [useMarkdown, renderMessages])

  // ── Layout ──
  return (
    <div className="h-full flex flex-col bg-bg overflow-hidden">
      <Toolbar
        models={models} selectedModel={selectedModel} onModelChange={setSelectedModel}
        temperature={temperature} onTemperatureChange={setTemperature}
        onToggleSidebar={() => setSidebarOpen(o => !o)} onNewChat={newChat}
        onOpenSettings={() => { setSettingsTab('general'); setSettingsOpen(true) }}
        tokenCount={tokenCount}
        onCopyConversation={copyConversation}
        hasMessages={messages.length > 0}
      />

      {/* Options bar */}
      <div className="flex items-center gap-4 px-4 py-1.5 bg-bg-surface border-b border-border fs-ui-xs font-sans">
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useMarkdown} onChange={e => setUseMarkdown(e.target.checked)} className="accent-accent w-3.5 h-3.5" />
          Markdown
        </label>
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useWebSearch} onChange={e => setUseWebSearch(e.target.checked)} className="accent-accent w-3.5 h-3.5" />
          Web Search
        </label>
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useReasoning} onChange={e => setUseReasoning(e.target.checked)} className="accent-accent w-3.5 h-3.5" />
          Reasoning
        </label>
        <div className="ml-auto flex items-center gap-3">
          <button onClick={() => { setSettingsTab('prompts'); setSettingsOpen(true) }} className="text-text-muted hover:text-accent transition-colors">Prompts</button>
          <select value={selectedPrompt || ''} onChange={e => setSelectedPrompt(e.target.value || null)}
                  className="bg-bg-elevated text-text-muted border border-border rounded px-2 py-0.5 fs-ui-xs max-w-[200px]">
            <option value="">No system prompt</option>
            {prompts.map(p => <option key={p.id} value={p.prompt_text}>{p.name}</option>)}
          </select>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} conversations={conversations}
                 currentConvId={currentConvId} onSelect={loadConversation} onDelete={deleteConversation}
                 onRename={renameConversation} onNew={newChat} />
        <ChatView messages={messages} isStreaming={isStreaming} streamContent={streamContent} streamModel={streamModel}
                  useMarkdown={useMarkdown} onEdit={editMessage} onRegenerate={regenerateMessage} onDelete={deleteMessage}
                  error={error} onDismissError={() => setError(null)} />
      </div>

      <InputBar onSend={sendMessage} onStop={stopGeneration} isStreaming={isStreaming} onAttach={attachFiles}
                stagedFiles={stagedFiles} onRemoveFile={removeStagedFile} apiKeySet={apiKeySet}
                onOpenSettings={() => { setSettingsTab('api'); setSettingsOpen(true) }} />

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} tab={settingsTab} onTabChange={setSettingsTab}
                     models={models} onModelsChange={setModels} prompts={prompts} onPromptsChange={setPrompts}
                     onApiKeyChange={setApiKeySet} fontSettings={fontSettings}
                     onFontSettingsChange={updated => { setFontSettings(updated); applyFontSettings(updated) }} />
    </div>
  )
}
