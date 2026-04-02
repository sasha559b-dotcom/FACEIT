import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { Avatar, RoleBadge, EloBar, RankInfo, Spinner } from '../components/UI'
import api from '../api'

const RANK_ORDER = ['Iron','Bronze','Silver','Gold','Platinum','Diamond','Master','Grandmaster']

export default function HomePage() {
  const { user, refreshUser } = useStore()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [recentMatches, setRecentMatches] = useState([])

  useEffect(() => {
    refreshUser()
    api.get('/matches/?limit=5').then(r => setRecentMatches(r.data)).catch(() => {})
  }, [])

  if (!user) return null
  const total = user.wins + user.losses
  const wr = total > 0 ? Math.round(user.wins / total * 100) : 0

  return (
    <div style={{ padding: '16px 16px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.6rem',
          letterSpacing: 3, color: 'var(--brand)', textTransform: 'uppercase'
        }}>
          ⚡ FaceitTG
        </div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-3)' }}>
          {new Date().toLocaleDateString('en', { weekday: 'short', day: 'numeric', month: 'short' })}
        </div>
      </div>

      {/* Player card */}
      <div className="card" style={{
        padding: 20,
        background: 'linear-gradient(135deg, var(--bg-1) 60%, rgba(255,107,0,0.08))'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
          <Avatar username={user.username} color={user.avatar_color} size={52} role={user.role} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.2rem' }}>
                {user.username}
              </span>
              <RoleBadge role={user.role} />
            </div>
            <div style={{ color: 'var(--text-3)', fontSize: '0.82rem', marginTop: 2 }}>
              🎮 {user.game_id}
            </div>
            <div style={{ marginTop: 6 }}>
              <RankInfo rankInfo={getRankInfo(user.elo)} elo={user.elo} />
            </div>
          </div>
        </div>
        <EloBar elo={user.elo} />
        <div style={{ display: 'flex', gap: 0, marginTop: 16 }}>
          {[
            { label: 'Wins', value: user.wins, color: '#10b981' },
            { label: 'Losses', value: user.losses, color: '#ef4444' },
            { label: 'W/R', value: `${wr}%`, color: wr >= 50 ? '#10b981' : '#f59e0b' },
            { label: 'ELO', value: user.elo, color: 'var(--brand)' },
          ].map((s, i) => (
            <div key={s.label} style={{
              flex: 1, textAlign: 'center',
              borderLeft: i > 0 ? '1px solid var(--border)' : 'none'
            }}>
              <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.3rem', color: s.color }}>
                {s.value}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status banners */}
      {user.is_banned && (
        <div style={{
          background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: 10, padding: '12px 16px', color: '#ef4444',
          fontWeight: 600, fontSize: '0.9rem'
        }}>
          🚫 You are banned: {user.ban_reason || 'No reason given'}
        </div>
      )}
      {user.is_muted && (
        <div style={{
          background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)',
          borderRadius: 10, padding: '12px 16px', color: '#f59e0b',
          fontWeight: 600, fontSize: '0.9rem'
        }}>
          🔇 You are muted: {user.mute_reason || 'No reason given'}
        </div>
      )}

      {/* Quick actions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <button className="card card-hover" style={{
          padding: '18px 14px', border: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
          cursor: 'pointer', background: 'none'
        }} onClick={() => navigate('/lobbies')}>
          <span style={{ fontSize: 28 }}>🎮</span>
          <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-1)', letterSpacing: 1, textTransform: 'uppercase' }}>
            Play Now
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>Find a lobby</span>
        </button>
        <button className="card card-hover" style={{
          padding: '18px 14px', border: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
          cursor: 'pointer', background: 'none'
        }} onClick={() => navigate('/leaderboard')}>
          <span style={{ fontSize: 28 }}>🏆</span>
          <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-1)', letterSpacing: 1, textTransform: 'uppercase' }}>
            Leaderboard
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>See rankings</span>
        </button>
      </div>

      {/* Recent matches */}
      {recentMatches.length > 0 && (
        <div>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1rem', letterSpacing: 1, color: 'var(--text-2)', textTransform: 'uppercase', marginBottom: 10 }}>
            Recent Matches
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentMatches.map(m => (
              <div key={m.id} className="card card-hover" style={{
                padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer'
              }} onClick={() => navigate(`/match/${m.id}`)}>
                <div style={{
                  width: 36, height: 36, borderRadius: 8, background: 'var(--bg-3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0
                }}>🗺️</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{m.map || 'Unknown Map'}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
                    {m.status === 'finished' ? `${m.score_team1} - ${m.score_team2}` : 'In progress'}
                  </div>
                </div>
                <div style={{
                  fontSize: '0.78rem', color: m.status === 'finished' ? '#10b981' : '#f59e0b',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1
                }}>
                  {m.status === 'finished' ? 'DONE' : 'LIVE'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ height: 8 }} />
    </div>
  )
}

function getRankInfo(elo) {
  if (elo < 800) return { name: 'Iron', color: '#6b7280', icon: '🪨' }
  if (elo < 1000) return { name: 'Bronze', color: '#92400e', icon: '🥉' }
  if (elo < 1200) return { name: 'Silver', color: '#9ca3af', icon: '🥈' }
  if (elo < 1500) return { name: 'Gold', color: '#f59e0b', icon: '🥇' }
  if (elo < 1800) return { name: 'Platinum', color: '#6366f1', icon: '💎' }
  if (elo < 2100) return { name: 'Diamond', color: '#06b6d4', icon: '💠' }
  if (elo < 2500) return { name: 'Master', color: '#8b5cf6', icon: '👑' }
  return { name: 'Grandmaster', color: '#ef4444', icon: '🔥' }
}
