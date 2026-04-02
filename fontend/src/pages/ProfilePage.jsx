import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { Avatar, RoleBadge, EloBar, RankInfo } from '../components/UI'
import api from '../api'

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

export default function ProfilePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, logout } = useStore()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  const profileId = id || user?.id

  useEffect(() => {
    if (!profileId) return
    api.get(`/users/${profileId}`).then(r => setProfile(r.data)).finally(() => setLoading(false))
  }, [profileId])

  if (loading) return (
    <div style={{ padding: 16 }}>
      <div className="skeleton" style={{ height: 180, borderRadius: 12, marginBottom: 16 }} />
      <div className="skeleton" style={{ height: 100, borderRadius: 12 }} />
    </div>
  )

  if (!profile) return (
    <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-3)', paddingTop: 60 }}>
      User not found
    </div>
  )

  const isOwnProfile = profile.id === user?.id
  const total = profile.wins + profile.losses
  const wr = total > 0 ? Math.round(profile.wins / total * 100) : 0
  const rankInfo = getRankInfo(profile.elo)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Hero banner */}
      <div style={{
        padding: '32px 20px 24px', position: 'relative', overflow: 'hidden',
        background: `linear-gradient(135deg, var(--bg-0) 0%, ${profile.avatar_color}20 100%)`,
        borderBottom: '1px solid var(--border)'
      }}>
        {id && (
          <button onClick={() => navigate(-1)} style={{
            position: 'absolute', top: 16, left: 16,
            background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
            width: 34, height: 34, cursor: 'pointer', color: 'var(--text-1)', fontSize: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>←</button>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
          <div style={{ position: 'relative' }}>
            <Avatar username={profile.username} color={profile.avatar_color} size={72} role={profile.role} />
            {profile.is_banned && (
              <div style={{ position: 'absolute', bottom: -4, right: -4, fontSize: 20 }}>🚫</div>
            )}
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.6rem', letterSpacing: 2, marginBottom: 4 }}>
              {profile.username}
            </div>
            <RoleBadge role={profile.role} />
            <div style={{ color: 'var(--text-3)', fontSize: '0.82rem', marginTop: 8 }}>
              🎮 {profile.game_id}
            </div>
            <div style={{ marginTop: 10 }}>
              <span style={{
                fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.3rem',
                color: rankInfo.color
              }}>
                {rankInfo.icon} {rankInfo.name}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ padding: '16px 16px 0', display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* ELO card */}
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, letterSpacing: 1, color: 'var(--text-2)', textTransform: 'uppercase', fontSize: '0.85rem' }}>
              ELO Rating
            </span>
            <span style={{
              fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.6rem',
              color: rankInfo.color
            }}>
              {profile.elo}
            </span>
          </div>
          <EloBar elo={profile.elo} />
        </div>

        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
          {[
            { label: 'Wins', value: profile.wins, color: '#10b981', icon: '✅' },
            { label: 'Losses', value: profile.losses, color: '#ef4444', icon: '❌' },
            { label: 'Win Rate', value: `${wr}%`, color: wr >= 50 ? '#10b981' : '#f59e0b', icon: '📊' },
            { label: 'Matches', value: total, color: 'var(--text-1)', icon: '🎮' },
          ].map(s => (
            <div key={s.label} className="card" style={{ padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 22, marginBottom: 6 }}>{s.icon}</div>
              <div style={{
                fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.5rem', color: s.color
              }}>
                {s.value}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>

        {/* Ban/mute info */}
        {profile.is_banned && (
          <div style={{
            background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 10, padding: '12px 16px'
          }}>
            <div style={{ color: '#ef4444', fontWeight: 700, marginBottom: 4 }}>🚫 BANNED</div>
            <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>{profile.ban_reason || 'No reason'}</div>
          </div>
        )}
        {profile.is_muted && (
          <div style={{
            background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)',
            borderRadius: 10, padding: '12px 16px'
          }}>
            <div style={{ color: '#f59e0b', fontWeight: 700, marginBottom: 4 }}>🔇 MUTED</div>
            <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>{profile.mute_reason || 'No reason'}</div>
          </div>
        )}

        {/* Actions */}
        {isOwnProfile && (
          <button className="btn-danger" style={{ padding: 14 }} onClick={logout}>
            🚪 LOGOUT
          </button>
        )}
      </div>
      <div style={{ height: 16 }} />
    </div>
  )
}
