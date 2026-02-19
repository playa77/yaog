import { useState } from 'react'
import { Copy, Check, Pencil, RefreshCw, Trash2 } from 'lucide-react'
import type { DisplayMessage } from '../App'
import Tooltip from './Tooltip'

interface Props {
  message: DisplayMessage
  onEdit: (index: number, content: string) => void
  onRegenerate: (index: number) => void
  onDelete: (index: number) => void
  disabled: boolean
}

export default function MessageBubble({ message, onEdit, onRegenerate, onDelete, disabled }: Props) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [copied, setCopied] = useState(false)

  const isUser = message.role === 'user'

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.raw)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Fallback for Electron
      const text = await window.api.chatGetMessages()
      const msg = text.find((_m: any, i: number) => i === message.index)
      if (msg) {
        await navigator.clipboard.writeText(msg.content)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }
    }
  }

  const startEdit = () => {
    setEditText(message.raw)
    setEditing(true)
  }

  const saveEdit = () => {
    if (editText.trim()) {
      onEdit(message.index, editText.trim())
    }
    setEditing(false)
  }

  return (
    <div className={`group relative py-5 ${isUser ? 'border-l-2 border-accent pl-6 bg-accent-dim/50 -mx-2 px-8 rounded-sm' : ''} mb-1`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`font-sans text-[11px] font-bold uppercase tracking-[1.2px] ${isUser ? 'text-accent' : 'text-text-muted'}`}>
          {isUser ? 'You' : message.model}
        </span>

        {/* Actions — visible on hover */}
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Tooltip text="Copy">
            <button onClick={handleCopy} disabled={disabled}
                    className="p-1 rounded text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors disabled:opacity-30">
              {copied ? <Check size={13} className="text-accent" /> : <Copy size={13} />}
            </button>
          </Tooltip>
          {isUser && (
            <Tooltip text="Edit">
              <button onClick={startEdit} disabled={disabled}
                      className="p-1 rounded text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors disabled:opacity-30">
                <Pencil size={13} />
              </button>
            </Tooltip>
          )}
          {!isUser && (
            <Tooltip text="Regenerate">
              <button onClick={() => { if (confirm('Regenerate this response?')) onRegenerate(message.index) }} disabled={disabled}
                      className="p-1 rounded text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors disabled:opacity-30">
                <RefreshCw size={13} />
              </button>
            </Tooltip>
          )}
          <Tooltip text="Delete">
            <button onClick={() => { if (confirm('Delete this and all following?')) onDelete(message.index) }} disabled={disabled}
                    className="p-1 rounded text-text-muted hover:text-danger hover:bg-danger/10 transition-colors disabled:opacity-30">
              <Trash2 size={13} />
            </button>
          </Tooltip>
        </div>
      </div>

      {/* Content */}
      {editing ? (
        <div>
          <textarea
            autoFocus
            value={editText}
            onChange={e => setEditText(e.target.value)}
            className="w-full min-h-[100px] bg-bg-surface text-text-bright border border-accent rounded-lg p-3 font-body text-chat resize-y focus:outline-none"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button onClick={() => setEditing(false)}
                    className="px-3 py-1.5 rounded-md bg-bg-elevated text-text-muted border border-border text-xs font-sans font-semibold hover:bg-bg-hover transition-colors">
              Cancel
            </button>
            <button onClick={saveEdit}
                    className="px-3 py-1.5 rounded-md bg-accent text-accent-text text-xs font-sans font-bold hover:bg-accent-hover transition-colors">
              Save & Re-run
            </button>
          </div>
        </div>
      ) : (
        <div
          className={`prose-chat ${isUser ? 'text-text' : 'text-text-bright'}`}
          dangerouslySetInnerHTML={{ __html: message.html }}
        />
      )}
    </div>
  )
}
