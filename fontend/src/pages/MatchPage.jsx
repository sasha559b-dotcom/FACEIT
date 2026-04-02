import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Avatar } from '../components/UI'
import api from '../api'

export default function MatchPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [match, setMatch] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/matches/${id}`).then(r => setMatch(r.data)).finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div style={{ padding: 16 }}>
      <div className="skeleton" style={{ height: 200, borderRadius: 12 }} />
    </div>
  )
  if (!match) return <div style={{ padding: 24, color: 'var(--text-3)', textAlign: 'center' }}>Match not found</div>

  return (
    <div style={{ padding: '0 0 16px' }}>
      <div style={{
        padding: '14px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 12
      }}>
        <button onClick={() => navigate(-1)} style={{
          background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
          width: 34, height: 34, cursor: 'pointer', color: 'var(--text-1)', fontSize: 16,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>←</button>
        <div>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.2rem', letterSpacing: 1 }}>
            MATCH #{match.id}
          </div>
          <div style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>
            {match.status === 'finished' ? '✅ Finished' : '▶ In Progress'} · 🗺️ {match.map || '?'}
          </div>
        </div>
      </div>

      <div style={{ padding: '16px 16px 0' }}>
        {/* Score */}
        {match.status === 'finished' && (
          <div className="card" style={{
            padding: 20, textAlign: 'center', marginBottom: 16,
            background: 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(239,68,68,0.1))'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '0.85rem', letterSpacing: 2, color: '#3b82f6', marginBottom: 4 }}>TEAM 1</div>
                <div style={{
                  fontFamily: 'Barlow Condensed', fontWeight: 900, fontSize: '3rem',
                  color: match.winner === 1 ? '#10b981' : '#ef4444',
                  lineHeight: 1
                }}>{match.score_team1}</div>
                {match.winner === 1 && <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 700, marginTop: 4 }}>WINNER</div>}
              </div>
              <div style={{ color: 'var(--text-3)', fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.5rem' }}>:</div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '0.85rem', letterSpacing: 2, color: '#ef4444', marginBottom: 4 }}>TEAM 2</div>
                <div style={{
                  fontFamily: 'Barlow Condensed', fontWeight: 900, fontSize: '3rem',
                  color: match.winner === 2 ? '#10b981' : '#ef4444',
                  lineHeight: 1
                }}>{match.score_team2}</div>
                {match.winner === 2 && <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 700, marginTop: 4 }}>WINNER</div>}
              </div>
            </div>
            {match.elo_change && (
              <div style={{ marginTop: 12, fontSize: '0.85rem', color: 'var(--text-3)' }}>
                ELO: Winners <span style={{ color: '#10b981', fontWeight: 700 }}>+{match.elo_change}</span> · Losers <span style={{ color: '#ef4444', fontWeight: 700 }}>-{match.elo_change}</span>
              </div>
            )}
          </div>
        )}

        {/* Teams */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { label: 'TEAM 1', color: '#3b82f6', players: match.team1_players || [], winner: match.winner === 1 },
            { label: 'TEAM 2', color: '#ef4444', players: match.team2_players || [], winner: match.winner === 2 },
          ].map(t => (
            <div key={t.label} style={{
              background: 'var(--bg-2)', borderRadius: 10, padding: 12,
              border: `1px solid ${t.winner ? t.color : 'var(--border)'}`,
            }}>
              <div style={{
                fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '0.9rem',
                letterSpacing: 2, color: t.color, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6
              }}>
                {t.label} {t.winner && '🏆'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {t.players.length ? t.players.map(p => (
                  <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}
                    onClick={() => navigate(`/profile/${p.id}`)} role="button" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Avatar username={p.username} color={p.avatar_color} size={26} />
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{p.username}</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>{p.elo} ELO</div>
                    </div>
                  </div>
                )) : (
                  <div style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>No players</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
