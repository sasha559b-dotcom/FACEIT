import React from 'react'

export function Avatar({ username, color, size = 36, role }) {
  const letter = username?.[0]?.toUpperCase() || '?'
  const roleColors = {
    developer: 'var(--brand)',
    admin: '#8b5cf6',
    moderator: '#3b82f6',
    player: color || '#6366f1',
  }
  const bg = roleColors[role] || color || '#6366f1'
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'Barlow Condensed', fontWeight: 800,
      fontSize: size * 0.42, color: 'white',
      flexShrink: 0, border: '2px solid rgba(255,255,255,0.1)'
    }}>
      {letter}
    </div>
  )
}

export function RoleBadge({ role }) {
  const cfg = {
    developer: { color: 'var(--brand)', bg: 'rgba(255,107,0,0.15)', label: '⚡ DEV' },
    admin: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)', label: '🛡️ ADMIN' },
    moderator: { color: '#3b82f6', bg: 'rgba(59,130,246,0.15)', label: '🔵 MOD' },
    player: { color: 'var(--text-3)', bg: 'transparent', label: '' },
  }
  const c = cfg[role] || cfg.player
  if (!c.label) return null
  return (
    <span className="badge" style={{ color: c.color, background: c.bg, border: `1px solid ${c.color}40` }}>
      {c.label}
    </span>
  )
}

export function EloBar({ elo }) {
  const max = 3000
  const pct = Math.min((elo / max) * 100, 100)
  const color = elo >= 2500 ? '#ef4444' : elo >= 2100 ? '#8b5cf6' : elo >= 1800 ? '#06b6d4'
    : elo >= 1500 ? '#6366f1' : elo >= 1200 ? '#f59e0b' : elo >= 1000 ? '#9ca3af' : '#6b7280'
  return (
    <div style={{ height: 4, background: 'var(--bg-3)', borderRadius: 2, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width 0.5s ease', borderRadius: 2 }} />
    </div>
  )
}

export function RankInfo({ rankInfo, elo }) {
  if (!rankInfo) return null
  return (
    <span style={{ color: rankInfo.color, fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.9rem' }}>
      {rankInfo.icon} {rankInfo.name} · {elo} ELO
    </span>
  )
}

export function Spinner({ size = 24 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `3px solid var(--bg-3)`,
      borderTop: `3px solid var(--brand)`,
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}

export function PageHeader({ title, subtitle, back, onBack }) {
  return (
    <div style={{ padding: '16px 16px 0', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
      {back && (
        <button onClick={onBack} style={{
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 8, width: 36, height: 36, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-1)', fontSize: 18, flexShrink: 0
        }}>←</button>
      )}
      <div>
        <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.3rem', letterSpacing: 1, textTransform: 'uppercase' }}>
          {title}
        </div>
        {subtitle && <div style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>{subtitle}</div>}
      </div>
    </div>
  )
}

export function StatusBadge({ status }) {
  const cfg = {
    waiting: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)', label: '⏳ WAITING' },
    picking: { color: '#6366f1', bg: 'rgba(99,102,241,0.15)', label: '🎯 PICKING' },
    in_progress: { color: '#10b981', bg: 'rgba(16,185,129,0.15)', label: '▶ LIVE' },
    finished: { color: 'var(--text-3)', bg: 'var(--bg-3)', label: '✓ DONE' },
  }
  const c = cfg[status] || cfg.waiting
  return (
    <span className="badge" style={{ color: c.color, background: c.bg }}>
      {c.label}
    </span>
  )
}

export function Toast({ msg, type = 'info', onClose }) {
  const colors = { success: '#10b981', error: '#ef4444', info: 'var(--brand)', warn: '#f59e0b' }
  React.useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [])
  return (
    <div style={{
      position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)',
      background: 'var(--bg-1)', border: `1px solid ${colors[type]}`,
      borderRadius: 10, padding: '10px 16px', zIndex: 9999,
      color: colors[type], fontFamily: 'Rajdhani', fontWeight: 600,
      fontSize: '0.95rem', maxWidth: '90vw', boxShadow: `0 4px 20px ${colors[type]}40`,
      animation: 'slide-up 0.3s ease',
    }}>
      {msg}
    </div>
  )
}

export function useToast() {
  const [toast, setToast] = React.useState(null)
  const show = (msg, type = 'info') => setToast({ msg, type })
  const hide = () => setToast(null)
  const el = toast ? <Toast msg={toast.msg} type={toast.type} onClose={hide} /> : null
  return { show, el }
}

export function Modal({ title, children, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
      zIndex: 200, animation: 'fade-in 0.2s ease'
    }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: 'var(--bg-1)', borderRadius: '16px 16px 0 0',
        width: '100%', maxWidth: 500, padding: 20,
        border: '1px solid var(--border)', borderBottom: 'none',
        animation: 'slide-up 0.3s ease', maxHeight: '85vh', overflow: 'auto'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.2rem', letterSpacing: 1 }}>
            {title}
          </span>
          <button onClick={onClose} style={{
            background: 'var(--bg-3)', border: '1px solid var(--border)',
            borderRadius: 6, width: 28, height: 28, cursor: 'pointer',
            color: 'var(--text-2)', fontSize: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}
