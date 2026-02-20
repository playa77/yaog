import { useState, useRef, useEffect } from 'react'
import { Copy, Check, Pencil, RefreshCw, Trash2, ChevronDown } from 'lucide-react'
import type { DisplayMessage } from '../App'
import Tooltip from './Tooltip'

interface Props {
  message: DisplayMessage
  onEdit: (index: number, content: string) => void
  onRegenerate: (index: number) => void
  onDelete: (index: number) => void
  disabled: boolean
  fullContent?: string // raw content WITH file blocks (for "copy with attachments")
}

/**
 * Strip markdown formatting to produce plain text.
 */
function stripMarkdown(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, (m) => m.replace(/```\w*\n?/g, '').replace(/```/g, ''))  // code blocks → just code
    .replace(/`([^`]+)`/g, '$1')            // inline code
    .replace(/#{1,6}\s+/g, '')              // headings
    .replace(/\*\*([^*]+)\*\*/g, '$1')      // bold
    .replace(/\*([^*]+)\*/g, '$1')          // italic
    .replace(/__([^_]+)__/g, '$1')          // bold alt
    .replace(/_([^_]+)_/g, '$1')            // italic alt
    .replace(/~~([^~]+)~~/g, '$1')          // strikethrough
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
    .replace(/^\s*[-*+]\s+/gm, '• ')       // list bullets
    .replace(/^\s*\d+\.\s+/gm, '')         // numbered lists
    .replace(/^>\s+/gm, '')                // blockquotes
    .replace(/---+/g, '')                   // hr
    .replace(/\n{3,}/g, '\n\n')            // collapse whitespace
    .trim()
}

export default function MessageBubble({ message, onEdit, onRegenerate, onDelete, disabled, fullContent }: Props) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [copied, setCopied] = useState(false)
  const [copyMenuOpen, setCopyMenuOpen] = useState(false)
  const copyMenuRef = useRef<HTMLDivElement>(null)

  const isUser = message.role === 'user'
  const hasAttachments = !!fullContent && fullContent.includes('yaog-file-content')

  // Close copy menu on outside click
  useEffect(() => {
    if (!copyMenuOpen) return
    const handler = (e: MouseEvent) => {
      if (copyMenuRef.current && !copyMenuRef.current.contains(e.target as Node)) {
        setCopyMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [copyMenuOpen])

  const flash = () => { setCopied(true); setTimeout(() => setCopied(false), 1500) }

  const doCopy = async (text: string) => {
    try {
      // Use Electron clipboard for reliability
      await window.api.clipboardWrite(text)
      flash()
    } catch {
      try { await navigator.clipboard.writeText(text); flash() } catch {}
    }
    setCopyMenuOpen(false)
  }

  const copyAsText = () => doCopy(stripMarkdown(message.raw))
  const copyAsMarkdown = () => doCopy(message.raw)
  const copyWithAttachments = () => {
    if (fullContent) doCopy(fullContent)
    else doCopy(message.raw)
  }

  const startEdit = () => { setEditText(message.raw); setEditing(true) }
  const saveEdit = () => { if (editText.trim()) onEdit(message.index, editText.trim()); setEditing(false) }

  return (
    <div className={`group relative py-5 ${isUser ? 'border-l-2 border-accent pl-6 bg-accent-dim/50 -mx-2 px-8 rounded-sm' : ''} mb-1`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`font-sans fs-ui-2xs font-bold uppercase tracking-[1.2px] ${isUser ? 'text-accent' : 'text-text-muted'}`}>
          {isUser ? 'You' : message.model}
        </span>

        {/* Actions — visible on hover */}
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* Copy dropdown */}
          <div className="relative" ref={copyMenuRef}>
            <Tooltip text="Copy">
              <div className="inline-flex">
                <button onClick={copyAsText} disabled={disabled}
                        className="p-1 rounded-l text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors disabled:opacity-30">
                  {copied ? <Check size={13} className="text-accent" /> : <Copy size={13} />}
                </button>
                <button onClick={() => setCopyMenuOpen(o => !o)} disabled={disabled}
                        className="p-1 rounded-r text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors disabled:opacity-30 -ml-px">
                  <ChevronDown size={10} />
                </button>
              </div>
            </Tooltip>

            {copyMenuOpen && (
              <div className="absolute right-0 top-full mt-1 z-50 bg-bg-surface border border-border rounded-lg shadow-xl py-1 min-w-[180px] animate-fade-in">
                <button onClick={copyAsText}
                        className="w-full text-left px-3 py-2 fs-ui-xs text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors">
                  Copy as Text
                </button>
                <button onClick={copyAsMarkdown}
                        className="w-full text-left px-3 py-2 fs-ui-xs text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors">
                  Copy as Markdown
                </button>
                {hasAttachments && (
                  <button onClick={copyWithAttachments}
                          className="w-full text-left px-3 py-2 fs-ui-xs text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors border-t border-border">
                    Copy with Attachments
                  </button>
                )}
              </div>
            )}
          </div>

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
            className="w-full min-h-[100px] bg-bg-surface text-text-bright border border-accent rounded-lg p-3 resize-y focus:outline-none input-chat"
          />
          <div className="flex justify-end gap-2 mt-2">
            <button onClick={() => setEditing(false)}
                    className="px-3 py-1.5 rounded-md bg-bg-elevated text-text-muted border border-border fs-ui-xs font-sans font-semibold hover:bg-bg-hover transition-colors">
              Cancel
            </button>
            <button onClick={saveEdit}
                    className="px-3 py-1.5 rounded-md bg-accent text-accent-text fs-ui-xs font-sans font-bold hover:bg-accent-hover transition-colors">
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
