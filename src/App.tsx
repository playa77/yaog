import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Plus } from 'lucide-react'
import { Marked } from 'marked'
import hljs from 'highlight.js'
import type { Conversation, Message, Model, SystemPrompt, FileAttachment, ChatOpts, LoadedConversation, DisplayMessage } from './types'
import { TabProvider, useTabContext } from './contexts/TabContext'
import Toolbar from './components/Toolbar'
import TabBar from './components/TabBar'
import TabContent from './components/TabContent'
import Sidebar from './components/Sidebar'
import SettingsSheet from './components/SettingsSheet'
import Tooltip from './components/Tooltip'

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


export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])

  return (
    <TabProvider conversations={conversations}>
      <AppInner conversations={conversations} setConversations={setConversations} />
    </TabProvider>
  )
}

function AppInner({ conversations, setConversations }: { 
  conversations: Conversation[], 
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>> 
}) {
  const { tabs, activeTabId, activeTab, openTab, closeTab, updateTab, loadConversationIntoNewTab, loadConversationIntoTab, saveTabToBackend, updateTabsForConversation, findTabByConversationId, switchTab } = useTabContext()

  // ── State synced with Active Tab ──
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [temperature, setTemperature] = useState(1.0)
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const [streamModel, setStreamModel] = useState('')
  const [pendingInput, setPendingInput] = useState('')
  const [stagedFiles, setStagedFiles] = useState<FileAttachment[]>([])
  const [error, setError] = useState<string | null>(null)

  // ── Tab init ──
  const initRef = useRef(false)
  useEffect(() => {
    if (initRef.current) return
    initRef.current = true
    if (tabs.length === 0) openTab()
  }, [tabs.length, openTab])

  // Sync state FROM activeTab
  const lastTabId = useRef<string | null>(null)
  useEffect(() => {
    if (!activeTab || activeTabId === lastTabId.current) return
    lastTabId.current = activeTabId

    setCurrentConvId(activeTab.conversationId)
    setMessages(activeTab.messages)
    setSelectedModel(activeTab.selectedModel)
    setTemperature(activeTab.temperature)
    setSelectedPrompt(activeTab.selectedPrompt)
    setUseWebSearch(activeTab.useWebSearch)
    setIsStreaming(activeTab.isStreaming)
    setStreamContent(activeTab.streamContent)
    setStreamModel(activeTab.streamModel)
    setPendingInput(activeTab.pendingInput)
    setStagedFiles(activeTab.stagedFiles)
    setError(activeTab.error)
  }, [activeTabId, activeTab])

  // Sync state TO activeTab
  useEffect(() => {
    if (!activeTabId) return
    const timer = setTimeout(() => {
      updateTab(activeTabId, {
        messages, selectedModel, temperature, selectedPrompt,
        useWebSearch, isStreaming, streamContent, streamModel,
        pendingInput, stagedFiles, error, conversationId: currentConvId
      })
    }, 100)
    return () => clearTimeout(timer)
  }, [
    activeTabId, messages, selectedModel, temperature, selectedPrompt, 
    useWebSearch, isStreaming, streamContent, streamModel, 
    pendingInput, stagedFiles, error, currentConvId, updateTab
  ])

  // ── Other State ──
  const [models, setModels] = useState<Model[]>([])
  const [prompts, setPrompts] = useState<SystemPrompt[]>([])
  const [useMarkdown, setUseMarkdown] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<string>('general')
  const [tokenCount, setTokenCount] = useState(0)
  const [apiKeySet, setApiKeySet] = useState(false)
  const [fontSettings, setFontSettings] = useState({
    chat_font_size: 16.5, chat_font_family: 'Literata',
    ui_font_size: 13, ui_font_family: 'Inter',
    mono_font_family: 'JetBrains Mono', mono_font_size: 14,
  })

  const streamContentRef = useRef('')

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

  useEffect(() => {
    async function init() {
      const [convs, mdls, prms, settings] = await Promise.all([
        window.api.convList(), window.api.modelsList(), window.api.promptsList(), window.api.settingsGet(),
      ])
      setConversations(convs); setModels(mdls); setPrompts(prms); setApiKeySet(settings.apiKeySet)
      if (mdls.length > 0) setSelectedModel(mdls[0].id)
      const fs = {
        chat_font_size: settings.chat_font_size ?? 16.5, chat_font_family: settings.chat_font_family ?? 'Literata',
        ui_font_size: settings.ui_font_size ?? 13, ui_font_family: settings.ui_font_family ?? 'Inter',
        mono_font_family: settings.mono_font_family ?? 'JetBrains Mono', mono_font_size: settings.mono_font_size ?? 14,
      }
      setFontSettings(fs); applyFontSettings(fs)
    }
    init()
  }, [applyFontSettings, setConversations])

  const activeTabIdRef = useRef(activeTabId)
  useEffect(() => { activeTabIdRef.current = activeTabId }, [activeTabId])

  const updateTabRef = useRef(updateTab)
  useEffect(() => { updateTabRef.current = updateTab }, [updateTab])

  useEffect(() => {
    setTokenCount(0)
    window.api.chatTokenCountFull(activeTabId, '').then(setTokenCount)
  }, [selectedPrompt, activeTabId])

  useEffect(() => {
    const timer = setTimeout(async () => {
      const count = await window.api.chatTokenCountFull(activeTabId, pendingInput)
      setTokenCount(count)
    }, 5000)
    return () => clearTimeout(timer)
  }, [pendingInput, activeTabId])

  // ── Helpers ──
  const renderMessages = useCallback((msgs: (Message & { idx?: number })[]): DisplayMessage[] => {
    return msgs.filter(m => m.role !== 'system').map(m => {
      const { text, filenames } = stripFileContent(m.content)
      const badges = attachmentBadgesHtml(filenames)
      const bodyHtml = useMarkdown
        ? renderMarkdown(text)
        : text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
      return {
        idx: m.idx ?? 0, role: m.role,
        html: badges + bodyHtml,
        raw: text,              // clean text only
        fullRaw: m.content,     // FULL content with file blocks
        model: m.model_used || 'AI',
      }
    })
  }, [useMarkdown])

  const refreshMessages = useCallback(async (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId)
    if (!tab || !tab.conversationId) return
    const msgs = await window.api.chatGetMessages(tabId)
    const rendered = renderMessages(msgs)
    updateTab(tabId, { messages: rendered })
    if (tabId === activeTabId) setMessages(rendered)
  }, [tabs, activeTabId, renderMessages, updateTab])

  const refreshMessagesRef = useRef(refreshMessages)
  useEffect(() => { refreshMessagesRef.current = refreshMessages }, [refreshMessages])

  const streamListenersRegistered = useRef(false)
  useEffect(() => {
    if (streamListenersRegistered.current) return
    streamListenersRegistered.current = true

    window.api.onStreamStart((tabId: string, _index: number, model: string) => {
      updateTabRef.current(tabId, { isStreaming: true, streamContent: '', streamModel: model })
      if (tabId === activeTabIdRef.current) {
        setIsStreaming(true); setStreamContent(''); setStreamModel(model); streamContentRef.current = ''
      }
    })
    window.api.onStreamToken((tabId: string, text: string) => {
      if (tabId === activeTabIdRef.current) {
        streamContentRef.current += text; setStreamContent(streamContentRef.current)
      }
      // Optional: update non-active tab state? (throttled)
    })
    window.api.onStreamDone(async (tabId: string, _content: string) => {
      await refreshMessagesRef.current(tabId)
      updateTabRef.current(tabId, { isStreaming: false, streamContent: '' })
      if (tabId === activeTabIdRef.current) {
        setIsStreaming(false); setStreamContent(''); streamContentRef.current = ''
        window.api.chatTokenCount(tabId).then(setTokenCount)
      }
    })
    window.api.onStreamError((tabId: string, msg: string) => {
      updateTabRef.current(tabId, { isStreaming: false, streamContent: '', error: msg })
      if (tabId === activeTabIdRef.current) {
        setIsStreaming(false); setStreamContent(''); streamContentRef.current = ''; setError(msg)
      }
    })
  }, [])

  useEffect(() => {
    if (activeTabId && activeTab?.conversationId && activeTab.messages.length === 0) {
      refreshMessages(activeTabId)
    }
  }, [activeTabId, activeTab?.conversationId])

  const chatOpts = useCallback((): ChatOpts => ({
    webSearch: useWebSearch,
  }), [useWebSearch])

  const webSearchTooltip = useMemo(() => `Web Search: ${useWebSearch ? 'On' : 'Off'}`, [useWebSearch])

  // ── Actions ──
  const loadConversation = useCallback(async (id: number) => {
    const existingTabId = findTabByConversationId(id)
    if (existingTabId) {
      await switchTab(existingTabId)
      return
    }
    if (activeTab && activeTab.messages.length === 0 && !activeTab.conversationId && !activeTab.isStreaming) {
      await loadConversationIntoTab(id, activeTabId)
    } else {
      await loadConversationIntoNewTab(id)
    }
  }, [activeTab, activeTabId, findTabByConversationId, loadConversationIntoTab, loadConversationIntoNewTab, switchTab])

  const newChat = useCallback(async () => {
    await window.api.convNew(); openTab()
  }, [openTab])

  const sendMessage = useCallback(async (text: string) => {
    if (activeTabId) await saveTabToBackend(activeTabId)
    if (isStreaming || (!text.trim() && stagedFiles.length === 0)) return
    const fileNames = stagedFiles.map(f => f.name)
    const badges = attachmentBadgesHtml(fileNames)
    let fullText = text
    for (const f of stagedFiles) fullText += `\n<div class="yaog-file-content" data-filename="${f.name}">\n--- START OF FILE: ${f.name} ---\n${f.content}\n--- END OF FILE: ${f.name} ---\n</div>`
    setStagedFiles([]); setError(null); setPendingInput('')
    const userHtml = useMarkdown ? renderMarkdown(text) : text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
    setMessages(prev => [...prev, {
      idx: -1,
      role: 'user' as const, html: badges + userHtml, raw: text, fullRaw: fullText, model: '',
    }])
    const result = await window.api.chatSend(activeTabId, fullText, selectedModel, temperature, selectedPrompt, chatOpts())
    if (result?.conversations) { 
      setConversations(result.conversations)
      if (!currentConvId && result.conversations.length > 0) {
        const newConv = result.conversations[0]
        setCurrentConvId(newConv.id)
        updateTab(activeTabId, { title: newConv.title, fullTitle: newConv.title, conversationId: newConv.id })
      }
    }
  }, [activeTabId, saveTabToBackend, isStreaming, stagedFiles, selectedModel, temperature, selectedPrompt, chatOpts, useMarkdown, currentConvId, setConversations, updateTab])

  const stopGeneration = useCallback(async () => { await window.api.chatStop(activeTabId) }, [activeTabId])

  const editMessage = useCallback(async (index: number, content: string) => {
    if (activeTabId) await saveTabToBackend(activeTabId)
    setError(null)
    const result = await window.api.chatEdit(activeTabId, index, content, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    setMessages(renderMessages(await window.api.chatGetMessages(activeTabId)))
  }, [activeTabId, saveTabToBackend, selectedModel, temperature, chatOpts, renderMessages, setConversations])

  const regenerateMessage = useCallback(async (index: number) => {
    if (activeTabId) await saveTabToBackend(activeTabId)
    setError(null)
    const result = await window.api.chatRegenerate(activeTabId, index, selectedModel, temperature, chatOpts())
    if (result?.conversations) setConversations(result.conversations)
    setMessages(renderMessages(await window.api.chatGetMessages(activeTabId)))
  }, [activeTabId, saveTabToBackend, selectedModel, temperature, chatOpts, renderMessages, setConversations])

  const deleteMessage = useCallback(async (index: number) => {
    if (activeTabId) await saveTabToBackend(activeTabId)
    const result = await window.api.chatDeleteMsg(activeTabId, index)
    if (result) { setMessages(renderMessages(result.messages)); setTokenCount(result.tokenCount) }
  }, [activeTabId, saveTabToBackend, renderMessages])

  const deleteConversation = useCallback(async (id: number) => {
    await window.api.convDelete(id); setConversations(prev => prev.filter(c => c.id !== id))
    tabs.filter(t => t.conversationId === id).forEach(t => closeTab(t.id))
  }, [setConversations, tabs, closeTab])

  const renameConversation = useCallback(async (id: number, title: string) => {
    await window.api.convRename(id, title); setConversations(prev => prev.map(c => c.id === id ? { ...c, title } : c))
    updateTabsForConversation(id, title)
  }, [setConversations, updateTabsForConversation])

  const attachFiles = useCallback(async () => {
    const files = await window.api.dialogOpenFiles()
    if (files.length > 0) setStagedFiles(prev => [...prev, ...files])
  }, [])

  const removeStagedFile = useCallback((name: string) => { setStagedFiles(prev => prev.filter(f => f.name !== name)) }, [])

  const copyConversation = useCallback(async (mode: 'text' | 'markdown' | 'full') => {
    if (activeTabId) await saveTabToBackend(activeTabId)
    const msgs = mode === 'full' ? await window.api.chatGetFullMessages(activeTabId) : await window.api.chatGetMessages(activeTabId)
    const parts: string[] = []
    for (const m of msgs) {
      if (m.role === 'system') { parts.push(`[System Prompt]\n${m.content}`); continue }
      const label = m.role === 'user' ? 'You' : (m.model_used || 'AI')
      if (mode === 'full') parts.push(`[${label}]\n${m.content}`)
      else if (mode === 'text') {
        const { text } = stripFileContent(m.content)
        parts.push(`[${label}]\n${stripMarkdown(text)}`)
      } else {
        const { text } = stripFileContent(m.content)
        parts.push(`[${label}]\n${text}`)
      }
    }
    const result = parts.join('\n\n---\n\n')
    await window.api.clipboardWrite(result)
  }, [activeTabId, saveTabToBackend])

  useEffect(() => {
    async function refresh() { 
      if (!activeTabId) return
      const msgs = await window.api.chatGetMessages(activeTabId); 
      if (msgs.length > 0) setMessages(renderMessages(msgs)) 
    }
    refresh()
  }, [useMarkdown, renderMessages, activeTabId])

  const selectedPromptMissing = Boolean(selectedPrompt) && !prompts.some(p => p.prompt_text === selectedPrompt)

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden">
      <Toolbar
        models={models} selectedModel={selectedModel} onModelChange={setSelectedModel}
        temperature={temperature} onTemperatureChange={setTemperature}
        onToggleSidebar={() => setSidebarOpen(o => !o)} onNewChat={newChat}
        onOpenSettings={() => { setSettingsTab('general'); setSettingsOpen(true) }}
        tokenCount={tokenCount}
        onCopyConversation={copyConversation}
        hasMessages={messages.length > 0}
      />

      <TabBar />

      {activeTab && (
        <div className="flex items-center gap-4 px-4 py-1.5 bg-bg-surface border-b border-border fs-ui-xs font-sans shrink-0">
          <div className="flex items-center gap-2 text-text-muted">
            <span className="select-none">Markdown</span>
            <Tooltip text={useMarkdown ? 'Markdown formatting enabled' : 'Plain text mode enabled'}>
              <input
                type="range" min={0} max={1} step={1} value={useMarkdown ? 1 : 0}
                onChange={e => setUseMarkdown(Number(e.target.value) >= 1)}
                className="w-[2.8rem] h-1 accent-accent cursor-pointer"
                aria-label="Markdown"
              />
            </Tooltip>
          </div>
          <div className="flex items-center gap-2 text-text-muted">
            <span className="select-none">Web Search</span>
            <Tooltip text={webSearchTooltip}>
              <input
                type="range" min={0} max={1} step={1} value={useWebSearch ? 1 : 0}
                onChange={e => setUseWebSearch(Number(e.target.value) >= 1)}
                className="w-[2.8rem] h-1 accent-accent cursor-pointer"
                aria-label="Web Search"
              />
            </Tooltip>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button onClick={() => { setSettingsTab('prompts'); setSettingsOpen(true) }} className="text-text-muted hover:text-accent transition-colors">Prompts</button>
            <select value={selectedPrompt || ''} onChange={e => setSelectedPrompt(e.target.value || null)}
                    className="bg-bg-elevated text-text-muted border border-border rounded px-2 py-0.5 fs-ui-xs max-w-[200px]">
              <option value="">No system prompt</option>
              {selectedPromptMissing && <option value={selectedPrompt || ''}>Loaded prompt (custom)</option>}
              {prompts.map(p => <option key={p.id} value={p.prompt_text}>{p.name}</option>)}
            </select>
          </div>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} conversations={conversations}
                 currentConvId={currentConvId} onOpenInNewTab={loadConversation} onDelete={deleteConversation}
                 onRename={renameConversation} onNew={newChat} />
        
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {tabs.length > 0 ? tabs.map(tab => (
            <TabContent
              key={tab.id}
              tab={tab}
              isActive={tab.id === activeTabId}
              useMarkdown={useMarkdown}
              apiKeySet={apiKeySet}
              onSendMessage={sendMessage}
              onStopGeneration={stopGeneration}
              onEditMessage={editMessage}
              onRegenerateMessage={regenerateMessage}
              onDeleteMessage={deleteMessage}
              onAttachFiles={attachFiles}
              onRemoveStagedFile={removeStagedFile}
              onInputChange={setPendingInput}
              onDismissError={() => setError(null)}
              onOpenSettings={(t) => { setSettingsTab(t); setSettingsOpen(true) }}
            />
          )) : (
            <div className="flex-1 flex flex-col items-center justify-center h-full text-center p-6 animate-fade-in">
              <div className="text-5xl mb-6 opacity-20">💬</div>
              <h2 className="text-text-bright font-sans fs-ui-3xl font-bold mb-3">Welcome to YaOG</h2>
              <p className="text-text-muted font-sans fs-ui-lg max-w-md mb-8 leading-relaxed">
                Open a conversation from history or start a fresh chat to begin.
              </p>
              <button
                onClick={newChat}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-accent text-accent-text font-sans font-semibold fs-ui-lg hover:bg-accent-hover transition-all shadow-lg hover:scale-[1.02] active:scale-[0.98]"
              >
                <Plus size={20} /> Start New Chat
              </button>
            </div>
          )}
        </div>
      </div>

      {activeTab && (
        <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} tab={settingsTab} onTabChange={setSettingsTab}
                       models={models} onModelsChange={setModels} prompts={prompts} onPromptsChange={setPrompts}
                       onApiKeyChange={setApiKeySet} fontSettings={fontSettings}
                       onFontSettingsChange={updated => { setFontSettings(updated); applyFontSettings(updated) }} />
      )}
    </div>
  )
}
