import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { Avatar, EloBar } from '../components/UI'
import api from '../api'

export default function LeaderboardPage() {
  const navigate = useNavigate()
  const { user } = useStore()
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/users/leaderboard').then(r => setPlayers(r.data)).finally(() => setLoading(false))
  }, [])

  const myPos = players.findIndex(p => p.id === user?.id) + 1

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.4rem', letterSpacing: 2, textTransform: 'uppercase' }}>
          🏆 Leaderboard
        </div>
        <div style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>
          {myPos > 0 ? `You are #${myPos}` : 'Top players by ELO'}
        </div>
      </div>

      {/* Top 3 podium */}
      {players.length >= 3 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'flex-end', justifyContent: 'center', height: 100 }}>
          {[players[1], players[0], players[2]].map((p, i) => {
            if (!p) return <div key={i} style={{ flex: 1 }} />
            const heights = [75, 100, 60]
            const colors = ['#9ca3af', '#f59e0b', '#92400e']
            const rank = [2, 1, 3]
            return (
              <div key={p.id} onClick={() => navigate(`/profile/${p.id}`)} style={{
                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'flex-end', cursor: 'pointer',
                height: heights[i], background: 'var(--bg-2)',
                borderRadius: '10px 10px 0 0',
                border: `1px solid var(--border)`,
                borderBottom: `3px solid ${colors[i]}`,
                padding: '8px 4px 4px', gap: 4
              }}>
                <Avatar username={p.username} color={p.avatar_color} size={28} role={p.role} />
                <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '0.75rem', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 60 }}>
                  {p.username}
                </div>
                <div style={{ fontSize: '0.7rem', color: colors[i], fontWeight: 700 }}>{p.elo}</div>
                <div style={{ fontSize: 14 }}>{['🥈','🥇','🥉'][i]}</div>
              </div>
            )
          })}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 62 }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {players.map((p, i) => {
            const isMe = p.id === user?.id
            return (
              <div key={p.id} className="card card-hover" style={{
                padding: '10px 14px', cursor: 'pointer',
                border: `1px solid ${isMe ? 'var(--brand)' : 'var(--border)'}`,
                background: isMe ? 'rgba(255,107,0,0.06)' : 'var(--bg-1)',
              }} onClick={() => navigate(`/profile/${p.id}`)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 28, fontFamily: 'Barlow Condensed', fontWeight: 800,
                    color: i < 3 ? ['#f59e0b','#9ca3af','#92400e'][i] : 'var(--text-3)',
                    fontSize: i < 3 ? '1rem' : '0.85rem', textAlign: 'center', flexShrink: 0
                  }}>
                    {i < 3 ? ['🥇','🥈','🥉'][i] : `#${p.rank}`}
                  </div>
                  <Avatar username={p.username} color={p.avatar_color} size={34} role={p.role} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{p.username}</span>
                      {isMe && <span style={{ fontSize: '0.7rem', color: 'var(--brand)', fontWeight: 700 }}>YOU</span>}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
                      {p.rank_info?.icon} {p.rank_info?.name} · {p.winrate}% WR
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{
                      fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.1rem',
                      color: p.rank_info?.color || 'var(--brand)'
                    }}>
                      {p.elo}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>
                      {p.wins}W {p.losses}L
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      <div style={{ height: 16 }} />
    </div>
  )
}
