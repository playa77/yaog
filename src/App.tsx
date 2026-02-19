import { useState, useEffect, useCallback, useRef } from 'react'
import { Marked } from 'marked'
import hljs from 'highlight.js'
import type { Conversation, Message, Model, SystemPrompt, FileAttachment, ChatOpts, AppSettings } from './types'
import Sidebar from './components/Sidebar'
import Toolbar from './components/Toolbar'
import ChatView from './components/ChatView'
import InputBar from './components/InputBar'
import SettingsSheet from './components/SettingsSheet'

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
  try {
    return marked.parse(content) as string
  } catch {
    return content.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
}

// ── Display message type ──
export interface DisplayMessage {
  index: number
  role: 'user' | 'assistant' | 'system'
  html: string
  raw: string
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
    chat_font_size: 16.5,
    chat_font_family: 'Literata',
    ui_font_size: 13,
    ui_font_family: 'DM Sans',
    mono_font_family: 'JetBrains Mono',
  })

  const streamContentRef = useRef('')

  // ── Apply font settings as CSS custom properties ──
  const applyFontSettings = useCallback((s: typeof fontSettings) => {
    const root = document.documentElement
    const serif = `'${s.chat_font_family}', Georgia, serif`
    const sans = `'${s.ui_font_family}', system-ui, sans-serif`
    const mono = `'${s.mono_font_family}', Consolas, monospace`
    root.style.setProperty('--font-chat', serif)
    root.style.setProperty('--font-ui', sans)
    root.style.setProperty('--font-mono', mono)
    root.style.setProperty('--size-chat', `${s.chat_font_size}px`)
    root.style.setProperty('--size-ui', `${s.ui_font_size}px`)

    // Ensure Google Fonts are loaded for any non-default families
    for (const family of [s.chat_font_family, s.ui_font_family, s.mono_font_family]) {
      const id = `gf-${family.replace(/\s+/g, '-').toLowerCase()}`
      if (!document.getElementById(id)) {
        const link = document.createElement('link')
        link.id = id
        link.rel = 'stylesheet'
        link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@400;500;600;700&display=swap`
        document.head.appendChild(link)
      }
    }
  }, [])

  // ── Init ──
  useEffect(() => {
    async function init() {
      const [convs, mdls, prms, settings] = await Promise.all([
        window.api.convList(),
        window.api.modelsList(),
        window.api.promptsList(),
        window.api.settingsGet(),
      ])
      setConversations(convs)
      setModels(mdls)
      setPrompts(prms)
      setApiKeySet(settings.apiKeySet)
      if (mdls.length > 0) setSelectedModel(mdls[0].id)

      // Apply font settings
      const fs = {
        chat_font_size: settings.chat_font_size ?? 16.5,
        chat_font_family: settings.chat_font_family ?? 'Literata',
        ui_font_size: settings.ui_font_size ?? 13,
        ui_font_family: settings.ui_font_family ?? 'DM Sans',
        mono_font_family: settings.mono_font_family ?? 'JetBrains Mono',
      }
      setFontSettings(fs)
      applyFontSettings(fs)
    }
    init()
  }, [applyFontSettings])

  // ── Stream event listeners ──
  useEffect(() => {
    window.api.onStreamStart((_index: number, model: string) => {
      setIsStreaming(true)
      setStreamContent('')
      setStreamModel(model)
      streamContentRef.current = ''
    })

    window.api.onStreamToken((text: string) => {
      streamContentRef.current += text
      setStreamContent(streamContentRef.current)
    })

    window.api.onStreamDone(async () => {
      setIsStreaming(false)
      setStreamContent('')
      streamContentRef.current = ''
      // Refresh messages from backend
      const msgs = await window.api.chatGetMessages()
      setMessages(renderMessages(msgs))
      const tc = await window.api.chatTokenCount()
      setTokenCount(tc)
    })

    window.api.onStreamError((msg: string) => {
      setIsStreaming(false)
      setStreamContent('')
      streamContentRef.current = ''
      setError(msg)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Helpers ──
  const renderMessages = useCallback((msgs: Message[]): DisplayMessage[] => {
    return msgs
      .filter(m => m.role !== 'system')
      .map((m, _i) => {
        // Find actual index (including system messages that were filtered)
        const realIndex = msgs.indexOf(m)
        return {
          index: realIndex,
          role: m.role,
          html: useMarkdown ? renderMarkdown(m.content) : m.content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>'),
          raw: m.content,
          model: m.model_used || 'AI',
        }
      })
  }, [useMarkdown])

  const chatOpts = useCallback((): ChatOpts => ({
    webSearch: useWebSearch,
    reasoning: useReasoning,
  }), [useWebSearch, useReasoning])

  // ── Actions ──
  const loadConversation = useCallback(async (id: number) => {
    const msgs = await window.api.convLoad(id)
    setCurrentConvId(id)
    setMessages(renderMessages(msgs))
    const tc = await window.api.chatTokenCount()
    setTokenCount(tc)
    setSidebarOpen(false)
  }, [renderMessages])

  const newChat = useCallback(async () => {
    await window.api.convNew()
    setCurrentConvId(null)
    setMessages([])
    setTokenCount(0)
    setSidebarOpen(false)
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming || (!text.trim() && stagedFiles.length === 0)) return

    // Append file content to message
    let fullText = text
    for (const f of stagedFiles) {
      fullText += `\n<div class="yaog-file-content" data-filename="${f.name}">\n--- START OF FILE: ${f.name} ---\n${f.content}\n--- END OF FILE: ${f.name} ---\n</div>`
    }
    setStagedFiles([])

    setError(null)

    // Optimistically add user message to display
    const userHtml = useMarkdown ? renderMarkdown(text) : text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
    setMessages(prev => [...prev, {
      index: prev.length > 0 ? prev[prev.length - 1].index + 1 : 0,
      role: 'user' as const,
      html: userHtml,
      raw: text,
      model: '',
    }])

    const result = await window.api.chatSend(fullText, selectedModel, temperature, selectedPrompt, chatOpts())
    if (result?.conversations) {
      setConversations(result.conversations)
      // Find the current conversation
      if (!currentConvId && result.conversations.length > 0) {
        setCurrentConvId(result.conversations[0].id)
      }
    }
  }, [isStreaming, stagedFiles, selectedModel, temperature, selectedPrompt, chatOpts, useMarkdown, currentConvId])

  const stopGeneration = useCallback(async () => {
    await window.api.chatStop()
  }, [])

  const editMessage = useCallback(async (index: number, content: string) => {
    setError(null)
    const result = await window.api.chatEdit(index, content, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    // Messages will refresh via stream events
    const msgs = await window.api.chatGetMessages()
    setMessages(renderMessages(msgs))
  }, [selectedModel, temperature, chatOpts, renderMessages])

  const regenerateMessage = useCallback(async (index: number) => {
    setError(null)
    const result = await window.api.chatRegenerate(index, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    const msgs = await window.api.chatGetMessages()
    setMessages(renderMessages(msgs))
  }, [selectedModel, temperature, chatOpts, renderMessages])

  const deleteMessage = useCallback(async (index: number) => {
    const result = await window.api.chatDeleteMsg(index)
    if (result) {
      setMessages(renderMessages(result.messages))
      setTokenCount(result.tokenCount)
    }
  }, [renderMessages])

  const deleteConversation = useCallback(async (id: number) => {
    await window.api.convDelete(id)
    setConversations(prev => prev.filter(c => c.id !== id))
    if (currentConvId === id) {
      setCurrentConvId(null)
      setMessages([])
      setTokenCount(0)
    }
  }, [currentConvId])

  const renameConversation = useCallback(async (id: number, title: string) => {
    await window.api.convRename(id, title)
    setConversations(prev => prev.map(c => c.id === id ? { ...c, title } : c))
  }, [])

  const attachFiles = useCallback(async () => {
    const files = await window.api.dialogOpenFiles()
    if (files.length > 0) setStagedFiles(prev => [...prev, ...files])
  }, [])

  const removeStagedFile = useCallback((name: string) => {
    setStagedFiles(prev => prev.filter(f => f.name !== name))
  }, [])

  // Re-render messages when markdown toggle changes
  useEffect(() => {
    async function refresh() {
      const msgs = await window.api.chatGetMessages()
      if (msgs.length > 0) setMessages(renderMessages(msgs))
    }
    refresh()
  }, [useMarkdown, renderMessages])

  // ── Layout ──
  return (
    <div className="h-full flex flex-col bg-bg overflow-hidden">
      {/* Toolbar */}
      <Toolbar
        models={models}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        temperature={temperature}
        onTemperatureChange={setTemperature}
        onToggleSidebar={() => setSidebarOpen(o => !o)}
        onNewChat={newChat}
        onOpenSettings={() => { setSettingsTab('general'); setSettingsOpen(true) }}
        tokenCount={tokenCount}
      />

      {/* Options bar */}
      <div className="flex items-center gap-4 px-4 py-1.5 bg-bg-surface border-b border-border text-xs font-sans">
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useMarkdown} onChange={e => setUseMarkdown(e.target.checked)}
                 className="accent-accent w-3.5 h-3.5" />
          Markdown
        </label>
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useWebSearch} onChange={e => setUseWebSearch(e.target.checked)}
                 className="accent-accent w-3.5 h-3.5" />
          Web Search
        </label>
        <label className="flex items-center gap-1.5 text-text-muted hover:text-text cursor-pointer select-none">
          <input type="checkbox" checked={useReasoning} onChange={e => setUseReasoning(e.target.checked)}
                 className="accent-accent w-3.5 h-3.5" />
          Reasoning
        </label>

        <div className="ml-auto flex items-center gap-3">
          <button onClick={() => { setSettingsTab('prompts'); setSettingsOpen(true) }}
                  className="text-text-muted hover:text-accent transition-colors">
            Prompts
          </button>
          <select
            value={selectedPrompt || ''}
            onChange={e => setSelectedPrompt(e.target.value || null)}
            className="bg-bg-elevated text-text-muted border border-border rounded px-2 py-0.5 text-xs max-w-[200px]"
          >
            <option value="">No system prompt</option>
            {prompts.map(p => (
              <option key={p.id} value={p.prompt_text}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 relative overflow-hidden">
        {/* Sidebar overlay */}
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          conversations={conversations}
          currentConvId={currentConvId}
          onSelect={loadConversation}
          onDelete={deleteConversation}
          onRename={renameConversation}
          onNew={newChat}
        />

        {/* Chat */}
        <ChatView
          messages={messages}
          isStreaming={isStreaming}
          streamContent={streamContent}
          streamModel={streamModel}
          useMarkdown={useMarkdown}
          onEdit={editMessage}
          onRegenerate={regenerateMessage}
          onDelete={deleteMessage}
          error={error}
          onDismissError={() => setError(null)}
        />
      </div>

      {/* Input bar */}
      <InputBar
        onSend={sendMessage}
        onStop={stopGeneration}
        isStreaming={isStreaming}
        onAttach={attachFiles}
        stagedFiles={stagedFiles}
        onRemoveFile={removeStagedFile}
        apiKeySet={apiKeySet}
        onOpenSettings={() => { setSettingsTab('api'); setSettingsOpen(true) }}
      />

      {/* Settings overlay */}
      <SettingsSheet
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        tab={settingsTab}
        onTabChange={setSettingsTab}
        models={models}
        onModelsChange={setModels}
        prompts={prompts}
        onPromptsChange={setPrompts}
        onApiKeyChange={setApiKeySet}
        fontSettings={fontSettings}
        onFontSettingsChange={(updated) => {
          setFontSettings(updated)
          applyFontSettings(updated)
        }}
      />
    </div>
  )
}
