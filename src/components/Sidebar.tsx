import { useState } from 'react'
import { X, Plus, Trash2, Pencil, Download, Upload } from 'lucide-react'
import type { Conversation } from '../types'
import Tooltip from './Tooltip'

interface Props {
  open: boolean
  onClose: () => void
  conversations: Conversation[]
  currentConvId: number | null
  onSelect: (id: number) => void
  onDelete: (id: number) => void
  onRename: (id: number, title: string) => void
  onNew: () => void
}

export default function Sidebar({
  open, onClose, conversations, currentConvId, onSelect, onDelete, onRename, onNew,
}: Props) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [contextId, setContextId] = useState<number | null>(null)

  const startRename = (c: Conversation) => {
    setEditingId(c.id)
    setEditTitle(c.title)
    setContextId(null)
  }

  const confirmRename = () => {
    if (editingId && editTitle.trim()) {
      onRename(editingId, editTitle.trim())
    }
    setEditingId(null)
  }

  const handleExport = async (id: number) => {
    const json = await window.api.convExport(id)
    const conv = conversations.find(c => c.id === id)
    await window.api.dialogSaveFile(`${conv?.title || 'chat'}.json`, json)
    setContextId(null)
  }

  const handleImport = async () => {
    const json = await window.api.dialogImportFile()
    if (json) {
      await window.api.convImport(json)
      // Refresh is done by parent
      onClose()
      window.location.reload() // Simple refresh for now
    }
  }

  return (
    <>
      {/* Scrim */}
      {open && (
        <div className="absolute inset-0 bg-black/50 z-30 animate-fade-in" onClick={onClose} />
      )}

      {/* Drawer */}
      <div className={`absolute top-0 left-0 bottom-0 w-80 bg-bg-surface border-r border-border z-40 flex flex-col transition-transform duration-250 ease-[cubic-bezier(0.16,1,0.3,1)] ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-border shrink-0">
          <h2 className="text-text-bright font-sans font-bold fs-ui-xl tracking-wide">Conversations</h2>
          <button onClick={onClose} className="p-1.5 rounded-md text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Actions */}
        <div className="flex gap-2 px-4 py-3 border-b border-border">
          <button onClick={onNew}
                  className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-accent text-accent-text font-sans font-semibold fs-ui-sm hover:bg-accent-hover transition-colors">
            <Plus size={16} /> New Chat
          </button>
          <Tooltip text="Import JSON">
            <button onClick={handleImport}
                    className="p-2 rounded-lg bg-bg-elevated text-text-muted hover:text-text-bright border border-border hover:border-border-light transition-colors">
              <Upload size={16} />
            </button>
          </Tooltip>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 && (
            <p className="text-text-muted fs-ui-sm text-center py-8 font-sans">No conversations yet</p>
          )}
          {conversations.map(c => (
            <div
              key={c.id}
              className={`group relative px-5 py-3.5 cursor-pointer border-b border-white/[0.03] transition-colors ${
                c.id === currentConvId
                  ? 'bg-bg-hover border-l-2 border-l-accent text-accent'
                  : 'text-text-muted hover:bg-bg-elevated hover:text-text'
              }`}
              onClick={() => { if (editingId !== c.id) onSelect(c.id) }}
              onContextMenu={e => { e.preventDefault(); setContextId(contextId === c.id ? null : c.id) }}
            >
              {editingId === c.id ? (
                <input
                  autoFocus
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') confirmRename(); if (e.key === 'Escape') setEditingId(null) }}
                  onBlur={confirmRename}
                  className="w-full bg-bg-elevated border border-accent rounded px-2 py-1 fs-ui-sm text-text-bright focus:outline-none"
                  onClick={e => e.stopPropagation()}
                />
              ) : (
                <span className="fs-ui-sm font-sans line-clamp-1">{c.title}</span>
              )}

              {/* Hover actions */}
              {editingId !== c.id && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                  <button onClick={e => { e.stopPropagation(); startRename(c) }}
                          className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-text-bright">
                    <Pencil size={13} />
                  </button>
                  <button onClick={e => { e.stopPropagation(); handleExport(c.id) }}
                          className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-text-bright">
                    <Download size={13} />
                  </button>
                  <button onClick={e => { e.stopPropagation(); if (confirm('Delete this conversation?')) onDelete(c.id) }}
                          className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-danger">
                    <Trash2 size={13} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
