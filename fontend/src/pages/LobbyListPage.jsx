import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { StatusBadge, Modal, useToast } from '../components/UI'
import api from '../api'

export default function LobbyListPage() {
  const navigate = useNavigate()
  const { user } = useStore()
  const [lobbies, setLobbies] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const { show, el } = useToast()

  const load = () => {
    setLoading(true)
    api.get('/lobbies/').then(r => setLobbies(r.data)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const createLobby = async () => {
    if (!name.trim()) return
    if (user?.is_banned) { show('You are banned', 'error'); return }
    setCreating(true)
    try {
      const res = await api.post('/lobbies/create', { name: name.trim() })
      navigate(`/lobby/${res.data.id}`)
    } catch (e) {
      show(e.message, 'error')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div style={{ padding: '16px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.4rem', letterSpacing: 2, textTransform: 'uppercase' }}>
            🎮 Lobbies
          </div>
          <div style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>Find or create a 5v5</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" style={{ padding: '8px 12px', fontSize: '0.85rem' }} onClick={load}>
            ↺ Refresh
          </button>
          <button className="btn-primary" style={{ padding: '8px 14px', fontSize: '0.85rem' }}
            onClick={() => setShowCreate(true)}>
            + Create
          </button>
        </div>
      </div>

      {loading && lobbies.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : lobbies.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '48px 0', color: 'var(--text-3)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12
        }}>
          <span style={{ fontSize: 48 }}>🎮</span>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-2)' }}>
            No lobbies yet
          </div>
          <div style={{ fontSize: '0.85rem' }}>Be the first to create one!</div>
          <button className="btn-primary" style={{ padding: '10px 24px' }} onClick={() => setShowCreate(true)}>
            + Create Lobby
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {lobbies.map(lobby => (
            <div key={lobby.id} className="card card-hover" style={{
              padding: '14px 16px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 8
            }} onClick={() => navigate(`/lobby/${lobby.id}`)}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1.05rem', letterSpacing: 1 }}>
                  {lobby.name}
                </div>
                <StatusBadge status={lobby.status} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: 12, fontSize: '0.82rem', color: 'var(--text-3)' }}>
                  <span>👥 {lobby.player_count}/10</span>
                  {lobby.map && <span>🗺️ {lobby.map}</span>}
                </div>
                <div style={{
                  display: 'flex', gap: 4
                }}>
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: i < lobby.player_count ? 'var(--brand)' : 'var(--bg-3)'
                    }} />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <Modal title="Create Lobby" onClose={() => setShowCreate(false)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>
                LOBBY NAME
              </label>
              <input
                className="input"
                style={{ padding: '12px 14px' }}
                placeholder="Epic 5v5 Match"
                value={name}
                onChange={e => setName(e.target.value)}
                maxLength={40}
                autoFocus
              />
            </div>
            <div style={{ background: 'var(--bg-2)', borderRadius: 8, padding: '10px 14px', fontSize: '0.82rem', color: 'var(--text-3)' }}>
              You will be captain of Team 1. Invite players by sharing the lobby link.
            </div>
            <button
              className="btn-primary"
              style={{ padding: 14 }}
              disabled={creating || !name.trim()}
              onClick={createLobby}
            >
              {creating ? '...' : '🎮 CREATE LOBBY'}
            </button>
          </div>
        </Modal>
      )}
      {el}
    </div>
  )
}
