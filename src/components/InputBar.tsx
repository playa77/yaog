import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Paperclip, Send, Square, X, AlertCircle } from 'lucide-react'
import type { FileAttachment } from '../types'
import Tooltip from './Tooltip'

interface Props {
  onSend: (text: string) => void
  onStop: () => void
  isStreaming: boolean
  onAttach: () => void
  stagedFiles: FileAttachment[]
  onRemoveFile: (name: string) => void
  apiKeySet: boolean
  onOpenSettings: () => void
}

export default function InputBar({
  onSend, onStop, isStreaming, onAttach, stagedFiles, onRemoveFile, apiKeySet, onOpenSettings,
}: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = '0'
      el.style.height = Math.min(el.scrollHeight, 180) + 'px'
    }
  }, [text])

  const handleSend = () => {
    if (isStreaming) { onStop(); return }
    if (!text.trim() && stagedFiles.length === 0) return
    onSend(text)
    setText('')
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!apiKeySet) {
    return (
      <div className="border-t border-border bg-bg-surface px-4 py-3 shrink-0">
        <button onClick={onOpenSettings}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-accent/10 border border-accent/20 text-accent font-sans font-semibold fs-ui-sm hover:bg-accent/20 transition-colors">
          <AlertCircle size={16} />
          Set your OpenRouter API key to start
        </button>
      </div>
    )
  }

  return (
    <div className="border-t border-border bg-bg-surface px-4 py-3 shrink-0">
      {/* Staged files */}
      {stagedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {stagedFiles.map(f => (
            <span key={f.name} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-elevated border border-border fs-ui-xs font-sans text-text-muted">
              📎 {f.name}
              <button onClick={() => onRemoveFile(f.name)} className="text-danger/60 hover:text-danger">
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        <Tooltip text="Attach files">
          <button onClick={onAttach}
                  className="p-2.5 rounded-xl text-text-muted hover:text-accent hover:bg-accent-dim transition-colors shrink-0 mb-0.5">
            <Paperclip size={18} />
          </button>
        </Tooltip>

        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Write your message… (Ctrl+Enter to send)"
          rows={1}
          className="flex-1 bg-bg-elevated text-text-bright border border-border rounded-xl px-4 py-3 input-chat resize-none focus:outline-none focus:border-accent/60 placeholder:text-text-muted/40 transition-colors"
        />

        <Tooltip text={isStreaming ? 'Stop' : 'Send (Ctrl+Enter)'}>
          <button
            onClick={handleSend}
            className={`p-2.5 rounded-xl shrink-0 mb-0.5 transition-colors ${
              isStreaming
                ? 'bg-danger text-white hover:bg-danger-hover'
                : 'bg-accent text-accent-text hover:bg-accent-hover'
            }`}
          >
            {isStreaming ? <Square size={18} /> : <Send size={18} />}
          </button>
        </Tooltip>
      </div>
    </div>
  )
}
