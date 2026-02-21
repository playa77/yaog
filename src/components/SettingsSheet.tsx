import { useState, useEffect, useCallback } from 'react'
import { X, Plus, Trash2, ChevronUp, ChevronDown, Eye, EyeOff, Save, RotateCcw, Pencil } from 'lucide-react'
import type { Model, SystemPrompt } from '../types'
import Tooltip from './Tooltip'

interface FontSettings {
  chat_font_size: number
  chat_font_family: string
  ui_font_size: number
  ui_font_family: string
  mono_font_family: string
  mono_font_size: number
}

interface Props {
  open: boolean
  onClose: () => void
  tab: string
  onTabChange: (tab: string) => void
  models: Model[]
  onModelsChange: (models: Model[]) => void
  prompts: SystemPrompt[]
  onPromptsChange: (prompts: SystemPrompt[]) => void
  onApiKeyChange: (set: boolean) => void
  fontSettings: FontSettings
  onFontSettingsChange: (settings: FontSettings) => void
}

const TABS = [
  { id: 'general', label: 'General' },
  { id: 'fonts', label: 'Fonts' },
  { id: 'api', label: 'API Key' },
  { id: 'models', label: 'Models' },
  { id: 'prompts', label: 'Prompts' },
]

export default function SettingsSheet({ open, onClose, tab, onTabChange, models, onModelsChange, prompts, onPromptsChange, onApiKeyChange, fontSettings, onFontSettingsChange }: Props) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex animate-fade-in">
      {/* Scrim */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Sheet */}
      <div className="relative m-auto w-full max-w-2xl max-h-[85vh] bg-bg-surface border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <h2 className="text-text-bright font-bold fs-ui-2xl">Settings</h2>
          <button onClick={onClose} className="p-1.5 rounded-md text-text-muted hover:text-text-bright hover:bg-bg-hover">
            <X size={18} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Tab nav */}
          <div className="w-40 shrink-0 border-r border-border bg-bg py-2">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => onTabChange(t.id)}
                className={`w-full text-left px-5 py-2.5 fs-ui-sm transition-colors ${
                  tab === t.id
                    ? 'text-accent bg-accent-dim border-l-2 border-accent font-semibold'
                    : 'text-text-muted hover:text-text hover:bg-bg-elevated'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-6">
            {tab === 'general' && <GeneralTab />}
            {tab === 'fonts' && <FontsTab fontSettings={fontSettings} onFontSettingsChange={onFontSettingsChange} />}
            {tab === 'api' && <ApiTab onApiKeyChange={onApiKeyChange} />}
            {tab === 'models' && <ModelsTab models={models} onModelsChange={onModelsChange} />}
            {tab === 'prompts' && <PromptsTab prompts={prompts} onPromptsChange={onPromptsChange} />}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── General Tab ──
function GeneralTab() {
  const [timeout, setTimeout_] = useState(360)
  const [confirmClose, setConfirmClose] = useState(true)

  useEffect(() => {
    window.api.settingsGet().then(s => {
      setTimeout_(s.api_timeout)
      setConfirmClose(s.confirm_close !== false)
    })
  }, [])

  return (
    <div className="space-y-6">
      <h3 className="text-text-bright font-semibold fs-ui-xl">General</h3>

      <div>
        <label className="block fs-ui-sm text-text-muted mb-1">API Timeout</label>
        <input type="number" min={10} max={600} value={timeout}
               onChange={e => { const v = parseInt(e.target.value) || 360; setTimeout_(v); window.api.settingsSet('api_timeout', v) }}
               className="w-24 bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2 fs-ui-sm focus:outline-none focus:border-accent" />
        <span className="text-text-muted fs-ui-xs ml-2">seconds</span>
      </div>

      <div>
        <label className="flex items-center gap-2.5 cursor-pointer select-none">
          <input type="checkbox" checked={confirmClose}
                 onChange={e => { setConfirmClose(e.target.checked); window.api.settingsSet('confirm_close', e.target.checked) }}
                 className="accent-accent w-4 h-4" />
          <span className="fs-ui-sm text-text-muted">Confirm before closing the app</span>
        </label>
      </div>

      <div className="pt-4 border-t border-border">
        <p className="text-text-muted fs-ui-xs">
          Data stored in <code className="text-accent fs-mono-sm">~/.yaog/</code>
        </p>
      </div>
    </div>
  )
}

// ── Fonts Tab ──

// Popular web-safe + Google Fonts options
const SERIF_FONTS = ['Literata', 'Georgia', 'Merriweather', 'Lora', 'Noto Serif', 'Crimson Pro', 'Source Serif 4', 'EB Garamond', 'Libre Baskerville', 'Playfair Display']
const SANS_FONTS  = ['DM Sans', 'Inter', 'Roboto', 'Open Sans', 'Lato', 'Noto Sans', 'Source Sans 3', 'Nunito', 'Poppins', 'Fira Sans', 'IBM Plex Sans', 'Ubuntu']
const MONO_FONTS  = ['JetBrains Mono', 'Fira Code', 'Source Code Pro', 'Roboto Mono', 'Ubuntu Mono', 'Inconsolata', 'IBM Plex Mono', 'Cascadia Code', 'Noto Sans Mono', 'Courier New']

const DEFAULTS: FontSettings = {
  chat_font_size: 16.5,
  chat_font_family: 'Literata',
  ui_font_size: 13,
  ui_font_family: 'DM Sans',
  mono_font_family: 'JetBrains Mono',
  mono_font_size: 14,
}

// Load a Google Font on demand
function ensureGoogleFont(name: string) {
  const id = `gf-${name.replace(/\s+/g, '-').toLowerCase()}`
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(name)}:wght@400;500;600;700&display=swap`
  document.head.appendChild(link)
}

function FontsTab({ fontSettings, onFontSettingsChange }: { fontSettings: FontSettings; onFontSettingsChange: (s: FontSettings) => void }) {
  const update = useCallback((key: keyof FontSettings, value: string | number) => {
    const next = { ...fontSettings, [key]: value }
    onFontSettingsChange(next)
    window.api.settingsSet(key, value)

    // Load Google Font if it's a family change
    if (typeof value === 'string' && key.endsWith('_family')) {
      ensureGoogleFont(value)
    }
  }, [fontSettings, onFontSettingsChange])

  const resetAll = useCallback(() => {
    onFontSettingsChange({ ...DEFAULTS })
    for (const [k, v] of Object.entries(DEFAULTS)) {
      window.api.settingsSet(k, v)
    }
  }, [onFontSettingsChange])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-text-bright font-semibold fs-ui-xl">Font Settings</h3>
        <Tooltip text="Reset all to defaults">
          <button onClick={resetAll}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg fs-ui-xs text-text-muted hover:text-accent hover:bg-accent-dim transition-colors">
            <RotateCcw size={12} /> Reset to defaults
          </button>
        </Tooltip>
      </div>

      {/* Chat body font */}
      <FontSection
        label="Chat / Message Body"
        description="The main body text for messages in conversations."
        fontFamily={fontSettings.chat_font_family}
        fontSize={fontSettings.chat_font_size}
        fontOptions={SERIF_FONTS}
        allowCustom
        onFamilyChange={v => update('chat_font_family', v)}
        onSizeChange={v => update('chat_font_size', v)}
        sizeMin={10} sizeMax={32} sizeStep={0.5}
        previewFont={fontSettings.chat_font_family}
        previewText="The adventurer stepped into the dimly lit cavern, torch flickering against ancient walls."
      />

      {/* UI font */}
      <FontSection
        label="Interface / Controls"
        description="Buttons, labels, sidebar, toolbar, settings — everything outside chat bubbles."
        fontFamily={fontSettings.ui_font_family}
        fontSize={fontSettings.ui_font_size}
        fontOptions={SANS_FONTS}
        allowCustom
        onFamilyChange={v => update('ui_font_family', v)}
        onSizeChange={v => update('ui_font_size', v)}
        sizeMin={9} sizeMax={24} sizeStep={0.5}
        previewFont={fontSettings.ui_font_family}
        previewText="New Chat · Settings · Temperature 0.70 · Web Search"
      />

      {/* Mono font — NOW WITH SIZE CONTROL */}
      <FontSection
        label="Code / Monospace"
        description="Code blocks, inline code, token counts, model IDs."
        fontFamily={fontSettings.mono_font_family}
        fontSize={fontSettings.mono_font_size}
        fontOptions={MONO_FONTS}
        allowCustom
        onFamilyChange={v => update('mono_font_family', v)}
        onSizeChange={v => update('mono_font_size', v)}
        sizeMin={9} sizeMax={24} sizeStep={0.5}
        previewFont={fontSettings.mono_font_family}
        previewText='const adventure = await openDoor("ancient_ruins");'
      />
    </div>
  )
}

interface FontSectionProps {
  label: string
  description: string
  fontFamily: string
  fontSize?: number
  fontOptions: string[]
  allowCustom?: boolean
  onFamilyChange: (v: string) => void
  onSizeChange?: (v: number) => void
  sizeMin?: number
  sizeMax?: number
  sizeStep?: number
  previewFont: string
  previewText: string
}

function FontSection({
  label, description, fontFamily, fontSize, fontOptions, allowCustom,
  onFamilyChange, onSizeChange, sizeMin, sizeMax, sizeStep,
  previewFont, previewText,
}: FontSectionProps) {
  const [customMode, setCustomMode] = useState(!fontOptions.includes(fontFamily))
  const [customValue, setCustomValue] = useState(fontFamily)

  const handleCustomSubmit = () => {
    if (customValue.trim()) {
      ensureGoogleFont(customValue.trim())
      onFamilyChange(customValue.trim())
    }
  }

  return (
    <div className="p-4 rounded-xl bg-bg-elevated/50 border border-border space-y-3">
      <div>
        <div className="fs-ui-sm text-text-bright font-semibold">{label}</div>
        <div className="fs-ui-xs text-text-muted mt-0.5">{description}</div>
      </div>

      <div className="flex items-end gap-3 flex-wrap">
        {/* Family picker */}
        <div className="flex-1 min-w-[180px]">
          <label className="block fs-ui-xs text-text-muted mb-1">Font Family</label>
          {customMode ? (
            <div className="flex gap-1.5">
              <input
                value={customValue}
                onChange={e => setCustomValue(e.target.value)}
                onBlur={handleCustomSubmit}
                onKeyDown={e => { if (e.key === 'Enter') handleCustomSubmit() }}
                placeholder="e.g. Atkinson Hyperlegible"
                className="flex-1 bg-bg text-text-bright border border-border rounded-lg px-3 py-2 fs-ui-sm focus:outline-none focus:border-accent"
              />
              <button onClick={() => { setCustomMode(false); onFamilyChange(fontOptions[0]) }}
                      className="px-2 py-2 rounded-lg fs-ui-xs text-text-muted hover:text-text bg-bg border border-border">
                List
              </button>
            </div>
          ) : (
            <div className="flex gap-1.5">
              <select
                value={fontFamily}
                onChange={e => onFamilyChange(e.target.value)}
                className="flex-1 bg-bg text-text-bright border border-border rounded-lg px-3 py-2 fs-ui-sm focus:outline-none focus:border-accent cursor-pointer"
              >
                {fontOptions.map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
              {allowCustom && (
                <Tooltip text="Type a custom font name">
                  <button onClick={() => { setCustomMode(true); setCustomValue(fontFamily) }}
                          className="px-2 py-2 rounded-lg fs-ui-xs text-text-muted hover:text-text bg-bg border border-border">
                    Custom
                  </button>
                </Tooltip>
              )}
            </div>
          )}
        </div>

        {/* Size slider */}
        {fontSize !== undefined && onSizeChange && (
          <div className="w-36">
            <label className="block fs-ui-xs text-text-muted mb-1">
              Size: <span className="text-accent font-semibold">{fontSize}px</span>
            </label>
            <input
              type="range"
              min={sizeMin} max={sizeMax} step={sizeStep}
              value={fontSize}
              onChange={e => onSizeChange(parseFloat(e.target.value))}
              className="w-full h-1.5 accent-accent cursor-pointer"
            />
            <div className="flex justify-between fs-ui-3xs text-text-muted mt-0.5">
              <span>{sizeMin}px</span>
              <span>{sizeMax}px</span>
            </div>
          </div>
        )}
      </div>

      {/* Live preview */}
      <div className="rounded-lg bg-bg p-3 border border-white/[0.03]">
        <div className="fs-ui-3xs text-text-muted uppercase tracking-wider mb-1.5 font-semibold">Preview</div>
        <div style={{ fontFamily: `'${previewFont}', sans-serif`, fontSize: fontSize ? `${fontSize}px` : '14px' }}
             className="text-text-bright leading-relaxed">
          {previewText}
        </div>
      </div>
    </div>
  )
}

// ── API Tab ──
function ApiTab({ onApiKeyChange }: { onApiKeyChange: (set: boolean) => void }) {
  const [key, setKey] = useState('')
  const [masked, setMasked] = useState('')
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    window.api.settingsGetApiKey().then(setMasked)
  }, [])

  const save = async () => {
    if (!key.trim()) return
    const ok = await window.api.settingsSaveApiKey(key.trim())
    if (ok) {
      setSaved(true)
      onApiKeyChange(true)
      setMasked(key.slice(0, 8) + '…' + key.slice(-4))
      setKey('')
      setTimeout(() => setSaved(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <h3 className="text-text-bright font-semibold fs-ui-xl">OpenRouter API Key</h3>

      {masked && (
        <p className="fs-ui-sm text-text-muted">
          Current key: <code className="text-accent fs-mono-sm">{ masked}</code>
        </p>
      )}

      <div className="flex gap-2">
        <div className="flex-1 relative">
          <input
            type={show ? 'text' : 'password'}
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="sk-or-v1-..."
            className="w-full bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2.5 pr-10 fs-ui-sm font-mono focus:outline-none focus:border-accent"
          />
          <button onClick={() => setShow(!show)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-bright">
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <button onClick={save}
                className="px-4 py-2.5 rounded-lg bg-accent text-accent-text font-semibold fs-ui-sm hover:bg-accent-hover transition-colors flex items-center gap-1.5">
          {saved ? <><Save size={14} /> Saved!</> : 'Save'}
        </button>
      </div>

      <p className="fs-ui-xs text-text-muted">
        Get your key at <span className="text-accent">openrouter.ai/keys</span>
      </p>
    </div>
  )
}

// ── Models Tab ──
function ModelsTab({ models, onModelsChange }: { models: Model[]; onModelsChange: (m: Model[]) => void }) {
  const [newName, setNewName] = useState('')
  const [newId, setNewId] = useState('')
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editId, setEditId] = useState('')
  const [confirmDeleteIdx, setConfirmDeleteIdx] = useState<number | null>(null)

  const add = async () => {
    if (!newName.trim() || !newId.trim()) return
    const result = await window.api.modelsAdd(newName.trim(), newId.trim())
    onModelsChange(result)
    setNewName('')
    setNewId('')
  }

  const startEdit = (idx: number) => {
    setEditIdx(idx)
    setEditName(models[idx].name)
    setEditId(models[idx].id)
    setConfirmDeleteIdx(null)
  }

  const cancelEdit = () => { setEditIdx(null); setEditName(''); setEditId('') }

  const saveEdit = async () => {
    if (editIdx === null || !editName.trim() || !editId.trim()) return
    const result = await window.api.modelsUpdate(editIdx, editName.trim(), editId.trim())
    onModelsChange(result)
    setEditIdx(null); setEditName(''); setEditId('')
  }

  const requestDelete = (idx: number) => {
    setConfirmDeleteIdx(idx)
    setEditIdx(null)
  }

  const confirmDelete = async () => {
    if (confirmDeleteIdx === null) return
    const result = await window.api.modelsDelete(confirmDeleteIdx)
    onModelsChange(result)
    setConfirmDeleteIdx(null)
  }

  const move = async (idx: number, dir: 'up' | 'down') => {
    const result = await window.api.modelsMove(idx, dir)
    onModelsChange(result)
  }

  return (
    <div className="space-y-4">
      <h3 className="text-text-bright font-semibold fs-ui-xl">Models</h3>

      <div className="space-y-1">
        {models.map((m, i) => (
          <div key={`${m.id}-${i}`}>
            {editIdx === i ? (
              /* ── Inline edit mode ── */
              <div className="py-2 px-3 rounded-lg bg-bg-elevated border border-accent/40 space-y-2">
                <input value={editName} onChange={e => setEditName(e.target.value)}
                       autoFocus
                       placeholder="Display name"
                       className="w-full bg-bg text-text-bright border border-border rounded-lg px-3 py-1.5 fs-ui-sm focus:outline-none focus:border-accent" />
                <input value={editId} onChange={e => setEditId(e.target.value)}
                       placeholder="Model ID"
                       className="w-full bg-bg text-text-bright border border-border rounded-lg px-3 py-1.5 fs-mono-sm focus:outline-none focus:border-accent" />
                <div className="flex gap-2">
                  <button onClick={saveEdit}
                          className="px-3 py-1.5 rounded-md bg-accent text-accent-text fs-ui-xs font-bold hover:bg-accent-hover transition-colors">
                    Save
                  </button>
                  <button onClick={cancelEdit}
                          className="px-3 py-1.5 rounded-md bg-bg text-text-muted border border-border fs-ui-xs font-semibold hover:bg-bg-hover transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            ) : confirmDeleteIdx === i ? (
              /* ── Inline delete confirmation ── */
              <div className="flex items-center gap-3 py-2 px-3 rounded-lg bg-danger/10 border border-danger/20">
                <span className="fs-ui-sm text-danger flex-1">Delete "{m.name}"?</span>
                <button onClick={confirmDelete}
                        className="px-3 py-1 rounded-md bg-danger text-white fs-ui-xs font-bold hover:bg-danger/80 transition-colors">
                  Delete
                </button>
                <button onClick={() => setConfirmDeleteIdx(null)}
                        className="px-3 py-1 rounded-md bg-bg text-text-muted border border-border fs-ui-xs font-semibold hover:bg-bg-hover transition-colors">
                  Cancel
                </button>
              </div>
            ) : (
              /* ── Normal display ── */
              <div className="flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-bg-elevated group cursor-pointer"
                   onDoubleClick={() => startEdit(i)}>
                <div className="flex-1 min-w-0">
                  <div className="fs-ui-sm text-text-bright truncate">{m.name}</div>
                  <div className="fs-mono-sm text-text-muted truncate">{m.id}</div>
                </div>
                <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Tooltip text="Move up">
                    <button onClick={() => move(i, 'up')} className="p-1 rounded text-text-muted hover:text-text-bright"><ChevronUp size={14} /></button>
                  </Tooltip>
                  <Tooltip text="Move down">
                    <button onClick={() => move(i, 'down')} className="p-1 rounded text-text-muted hover:text-text-bright"><ChevronDown size={14} /></button>
                  </Tooltip>
                  <Tooltip text="Edit">
                    <button onClick={() => startEdit(i)} className="p-1 rounded text-text-muted hover:text-accent"><Pencil size={14} /></button>
                  </Tooltip>
                  <Tooltip text="Delete">
                    <button onClick={() => requestDelete(i)} className="p-1 rounded text-text-muted hover:text-danger"><Trash2 size={14} /></button>
                  </Tooltip>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-border pt-4 space-y-2">
        <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Display name"
               className="w-full bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2 fs-ui-sm focus:outline-none focus:border-accent" />
        <input value={newId} onChange={e => setNewId(e.target.value)} placeholder="Model ID (e.g. anthropic/claude-3.5-sonnet)"
               className="w-full bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2 fs-mono-sm focus:outline-none focus:border-accent" />
        <button onClick={add}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-accent text-accent-text fs-ui-sm font-semibold hover:bg-accent-hover transition-colors">
          <Plus size={14} /> Add Model
        </button>
      </div>
    </div>
  )
}

// ── Prompts Tab ──
function PromptsTab({ prompts, onPromptsChange }: { prompts: SystemPrompt[]; onPromptsChange: (p: SystemPrompt[]) => void }) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [content, setContent] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const select = (p: SystemPrompt) => {
    setSelectedId(p.id)
    setName(p.name)
    setContent(p.prompt_text)
    setConfirmDeleteId(null)
  }

  const reset = () => {
    setSelectedId(null)
    setName('')
    setContent('')
  }

  const save = async () => {
    if (!name.trim() || !content.trim()) return
    const result = await window.api.promptsSave(selectedId, name.trim(), content.trim())
    onPromptsChange(result)
    reset()
  }

  const remove = async (id: number) => {
    const result = await window.api.promptsDelete(id)
    onPromptsChange(result)
    if (selectedId === id) reset()
    setConfirmDeleteId(null)
  }

  return (
    <div className="space-y-4">
      <h3 className="text-text-bright font-semibold fs-ui-xl">System Prompts</h3>

      {/* List */}
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {prompts.map(p => (
          <div key={p.id}>
            {confirmDeleteId === p.id ? (
              <div className="flex items-center gap-3 py-2 px-3 rounded-lg bg-danger/10 border border-danger/20 animate-fade-in">
                <span className="fs-ui-sm text-danger flex-1 truncate">Delete "{p.name}"?</span>
                <button onClick={() => remove(p.id)}
                        className="px-2.5 py-1 rounded-md bg-danger text-white fs-ui-xs font-bold hover:bg-danger/80 transition-colors">
                  Delete
                </button>
                <button onClick={() => setConfirmDeleteId(null)}
                        className="px-2.5 py-1 rounded-md bg-bg text-text-muted border border-border fs-ui-xs font-semibold hover:bg-bg-hover transition-colors">
                  Cancel
                </button>
              </div>
            ) : (
              <div
                onClick={() => select(p)}
                className={`flex items-center justify-between py-2 px-3 rounded-lg cursor-pointer group transition-colors ${
                  selectedId === p.id ? 'bg-accent-dim text-accent' : 'hover:bg-bg-elevated text-text-muted hover:text-text'
                }`}>
                <span className="fs-ui-sm truncate">{p.name}</span>
                <button onClick={e => { e.stopPropagation(); setConfirmDeleteId(p.id) }}
                        className="p-1 rounded text-text-muted hover:text-danger opacity-0 group-hover:opacity-100">
                  <Trash2 size={13} />
                </button>
              </div>
            )}
          </div>
        ))}
        {prompts.length === 0 && (
          <p className="text-text-muted fs-ui-sm py-2">No prompts yet. Create one below.</p>
        )}
      </div>

      <div className="border-t border-border pt-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="fs-ui-xs text-text-muted uppercase tracking-wide font-bold">
            {selectedId ? 'Edit Prompt' : 'New Prompt'}
          </span>
          {selectedId && (
            <button onClick={reset} className="fs-ui-xs text-accent hover:underline">+ New instead</button>
          )}
        </div>

        <input value={name} onChange={e => setName(e.target.value)}
               placeholder="Name (e.g. Fantasy DM, Code Reviewer)"
               className="w-full bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2 fs-ui-sm focus:outline-none focus:border-accent" />

        <textarea value={content} onChange={e => setContent(e.target.value)}
                  placeholder="You are a seasoned dungeon master who creates immersive, dark fantasy worlds…"
                  rows={6}
                  className="w-full bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-2.5 fs-ui-sm resize-y focus:outline-none focus:border-accent" />

        <button onClick={save}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-accent-text fs-ui-sm font-semibold hover:bg-accent-hover transition-colors">
          <Save size={14} /> {selectedId ? 'Update' : 'Save'}
        </button>
      </div>
    </div>
  )
}
