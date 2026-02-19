import { Menu, Plus, Settings, Thermometer } from 'lucide-react'
import type { Model } from '../types'
import Tooltip from './Tooltip'

interface Props {
  models: Model[]
  selectedModel: string
  onModelChange: (id: string) => void
  temperature: number
  onTemperatureChange: (t: number) => void
  onToggleSidebar: () => void
  onNewChat: () => void
  onOpenSettings: () => void
  tokenCount: number
}

export default function Toolbar({
  models, selectedModel, onModelChange, temperature, onTemperatureChange,
  onToggleSidebar, onNewChat, onOpenSettings, tokenCount,
}: Props) {
  return (
    <div className="flex items-center gap-2 px-3 h-12 bg-bg-surface border-b border-border shrink-0 font-sans">
      {/* Hamburger */}
      <Tooltip text="History">
        <button onClick={onToggleSidebar}
                className="p-2 rounded-lg text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors">
          <Menu size={20} />
        </button>
      </Tooltip>

      {/* New Chat */}
      <Tooltip text="New Chat">
        <button onClick={onNewChat}
                className="p-2 rounded-lg text-text-muted hover:text-accent hover:bg-accent-dim transition-colors">
          <Plus size={20} />
        </button>
      </Tooltip>

      <div className="w-px h-6 bg-border mx-1" />

      {/* Model selector */}
      <select
        value={selectedModel}
        onChange={e => onModelChange(e.target.value)}
        className="bg-bg-elevated text-text-bright border border-border rounded-lg px-3 py-1.5 text-sm font-semibold min-w-[180px] max-w-[300px] flex-1 hover:border-accent/50 transition-colors cursor-pointer focus:outline-none focus:border-accent"
      >
        {models.map(m => (
          <option key={m.id} value={m.id}>{m.name}</option>
        ))}
      </select>

      {/* Temperature */}
      <Tooltip text="Temperature">
        <div className="flex items-center gap-2 ml-2">
          <Thermometer size={14} className="text-text-muted" />
          <input
            type="range"
            min={0} max={40} value={Math.round(temperature * 20)}
            onChange={e => onTemperatureChange(parseInt(e.target.value) * 0.05)}
            className="w-20 h-1 accent-accent cursor-pointer"
          />
          <span className="text-xs font-mono text-accent font-bold w-8 text-center">
            {temperature.toFixed(2)}
          </span>
        </div>
      </Tooltip>

      <div className="flex-1" />

      {/* Token count */}
      {tokenCount > 0 && (
        <span className="text-[11px] font-mono text-text-muted">
          ~{tokenCount.toLocaleString()} tok
        </span>
      )}

      {/* Settings */}
      <Tooltip text="Settings">
        <button onClick={onOpenSettings}
                className="p-2 rounded-lg text-text-muted hover:text-text-bright hover:bg-bg-hover transition-colors">
          <Settings size={18} />
        </button>
      </Tooltip>
    </div>
  )
}
