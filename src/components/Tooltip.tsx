import { useState, useRef, useEffect, type ReactNode } from 'react'

interface Props {
  text: string
  children: ReactNode
  position?: 'top' | 'bottom'
}

export default function Tooltip({ text, children, position = 'top' }: Props) {
  const [visible, setVisible] = useState(false)
  const [coords, setCoords] = useState({ x: 0, y: 0 })
  const wrapRef = useRef<HTMLDivElement>(null)
  const tipRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const show = () => {
    timerRef.current = setTimeout(() => setVisible(true), 400)
  }

  const hide = () => {
    clearTimeout(timerRef.current)
    setVisible(false)
  }

  useEffect(() => {
    if (!visible || !wrapRef.current || !tipRef.current) return
    const wr = wrapRef.current.getBoundingClientRect()
    const tip = tipRef.current.getBoundingClientRect()

    let x = wr.left + wr.width / 2 - tip.width / 2
    let y = position === 'top'
      ? wr.top - tip.height - 6
      : wr.bottom + 6

    // Clamp to viewport
    if (x < 4) x = 4
    if (x + tip.width > window.innerWidth - 4) x = window.innerWidth - tip.width - 4
    if (y < 4) { y = wr.bottom + 6 } // flip to bottom if clipped at top

    setCoords({ x, y })
  }, [visible, position])

  useEffect(() => () => clearTimeout(timerRef.current), [])

  return (
    <div
      ref={wrapRef}
      onMouseEnter={show}
      onMouseLeave={hide}
      onMouseDown={hide}
      className="inline-flex"
    >
      {children}
      {visible && (
        <div
          ref={tipRef}
          className="fixed z-[9999] px-2.5 py-1 rounded-md bg-[#2A2D3A] text-text-bright text-xs font-sans whitespace-nowrap shadow-lg border border-white/[0.06] pointer-events-none animate-fade-in"
          style={{ left: coords.x, top: coords.y }}
        >
          {text}
        </div>
      )}
    </div>
  )
}
