import { useRef, useEffect } from 'react'
import { Marked } from 'marked'
import hljs from 'highlight.js'
import { AlertCircle, X } from 'lucide-react'
import MessageBubble from './MessageBubble'
import type { DisplayMessage } from '../App'

const marked = new Marked({
  gfm: true,
  renderer: {
    code({ text, lang }: { text: string; lang?: string }) {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted = hljs.highlight(text, { language }).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    },
  },
})

interface Props {
  messages: DisplayMessage[]
  isStreaming: boolean
  streamContent: string
  streamModel: string
  useMarkdown: boolean
  onEdit: (index: number, content: string) => void
  onRegenerate: (index: number) => void
  onDelete: (index: number) => void
  error: string | null
  onDismissError: () => void
}

export default function ChatView({
  messages, isStreaming, streamContent, streamModel, useMarkdown,
  onEdit, onRegenerate, onDelete, error, onDismissError,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamContent])

  let streamHtml = ''
  if (streamContent) {
    try {
      streamHtml = useMarkdown
        ? (marked.parse(streamContent) as string)
        : streamContent.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
    } catch { streamHtml = streamContent }
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 pb-20">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-[60vh] text-center">
            <div className="text-4xl mb-4 opacity-20">⚔️</div>
            <h2 className="text-text-muted font-sans fs-ui-2xl font-semibold mb-2">Ready for adventure</h2>
            <p className="text-text-muted/60 font-sans fs-ui-sm max-w-sm">
              Choose your model, set a system prompt for your world, and begin.
            </p>
          </div>
        )}

        {messages.map(m => (
          <MessageBubble
            key={`${m.index}-${m.role}`}
            message={m}
            onEdit={onEdit}
            onRegenerate={onRegenerate}
            onDelete={onDelete}
            disabled={isStreaming}
            fullContent={m.fullRaw}
          />
        ))}

        {isStreaming && (
          <div className="mb-2">
            <div className="flex items-center gap-2 mb-2.5 font-sans fs-ui-2xs font-bold uppercase tracking-[1.2px] text-text-muted">
              {streamModel}
            </div>
            {streamContent ? (
              <div className="prose-chat" dangerouslySetInnerHTML={{ __html: streamHtml }} />
            ) : (
              <div className="text-text-muted italic font-body animate-breathe">Composing…</div>
            )}
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-danger/10 border border-danger/20 mb-4 animate-fade-in">
            <AlertCircle size={18} className="text-danger shrink-0 mt-0.5" />
            <p className="fs-ui-sm font-sans text-danger flex-1">{error}</p>
            <button onClick={onDismissError} className="text-danger/60 hover:text-danger"><X size={16} /></button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
