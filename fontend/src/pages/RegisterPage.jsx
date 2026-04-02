import React, { useState, useEffect } from 'react'
import { useStore } from '../store'
import { useToast } from '../components/UI'

export default function RegisterPage() {
  const { register, setTelegramId, setInitData } = useStore()
  const [username, setUsername] = useState('')
  const [gameId, setGameId] = useState('')
  const [loading, setLoading] = useState(false)
  const { show, el } = useToast()
  const [step, setStep] = useState(1) // 1=nick, 2=gameid

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
      const user = tg.initDataUnsafe?.user
      if (user?.id) {
        setTelegramId(user.id)
        setInitData(tg.initData)
        if (user.username) setUsername(user.username)
      }
    }
  }, [])

  const handleSubmit = async () => {
    if (!username.trim() || !gameId.trim()) {
      show('Fill in all fields', 'error')
      return
    }
    const stored = JSON.parse(localStorage.getItem('faceit-tg-store') || '{}')
    const telegramId = stored?.state?.telegramId
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData || String(telegramId || Date.now())

    setLoading(true)
    try {
      await register(username.trim(), gameId.trim(), initData, telegramId)
      show('Welcome! 🎮', 'success')
    } catch (e) {
      show(e.message || 'Registration failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: 24, background: 'var(--bg-0)', position: 'relative', overflow: 'hidden'
    }}>
      {/* Background decor */}
      <div style={{
        position: 'absolute', width: 300, height: 300, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(255,107,0,0.12) 0%, transparent 70%)',
        top: -80, right: -60, pointerEvents: 'none'
      }} />
      <div style={{
        position: 'absolute', width: 200, height: 200, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%)',
        bottom: 60, left: -40, pointerEvents: 'none'
      }} />

      <div style={{ width: '100%', maxWidth: 360, zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 56, marginBottom: 12 }}>⚡</div>
          <div style={{
            fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '2.2rem',
            letterSpacing: 6, textTransform: 'uppercase', color: 'var(--brand)'
          }}>FaceitTG</div>
          <div style={{ color: 'var(--text-3)', fontSize: '0.9rem', marginTop: 6 }}>
            Competitive gaming platform
          </div>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1.1rem', letterSpacing: 1, color: 'var(--text-2)', textTransform: 'uppercase' }}>
            Create Account
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>
              NICKNAME
            </label>
            <input
              className="input"
              style={{ padding: '12px 14px' }}
              placeholder="your_nickname"
              value={username}
              onChange={e => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
              maxLength={20}
              autoFocus
            />
            <div style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
              3-20 chars, letters/numbers/_/-
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>
              GAME ID / NICKNAME IN-GAME
            </label>
            <input
              className="input"
              style={{ padding: '12px 14px' }}
              placeholder="YourGameNick#1234"
              value={gameId}
              onChange={e => setGameId(e.target.value)}
              maxLength={50}
            />
            <div style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
              Your in-game nickname or ID
            </div>
          </div>

          <button
            className="btn-primary"
            style={{ padding: '14px', fontSize: '1.05rem', width: '100%' }}
            disabled={loading || username.length < 3 || !gameId.trim()}
            onClick={handleSubmit}
          >
            {loading ? '...' : '🎮 JOIN NOW'}
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: 24, color: 'var(--text-3)', fontSize: '0.8rem' }}>
          Starting ELO: 1000 · Rank: Silver
        </div>
      </div>
      {el}
    </div>
  )
}
