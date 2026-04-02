import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { Avatar, StatusBadge, Modal, useToast } from '../components/UI'
import api from '../api'

const MAPS_POOL = ['Dust2','Mirage','Inferno','Nuke','Overpass','Ancient','Vertigo']
const MAP_ICONS = { Dust2:'🏜️', Mirage:'🏙️', Inferno:'🔥', Nuke:'☢️', Overpass:'🌉', Ancient:'🏛️', Vertigo:'🏗️' }

export default function LobbyPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useStore()
  const [lobby, setLobby] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showSubmit, setShowSubmit] = useState(false)
  const [score1, setScore1] = useState('')
  const [score2, setScore2] = useState('')
  const [winner, setWinner] = useState(1)
  const [matchId, setMatchId] = useState(null)
  const { show, el } = useToast()

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/lobbies/${id}`)
      setLobby(res.data)
      // Find associated match
      const matches = await api.get(`/matches/?limit=50`)
      const m = matches.data.find(m => m.lobby_id == id && m.status === 'in_progress')
      if (m) setMatchId(m.id)
    } catch (e) {
      if (e.message.includes('404')) navigate('/lobbies')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load])

  const action = async (fn) => {
    setActionLoading(true)
    try {
      const res = await fn()
      setLobby(res.data)
    } catch (e) {
      show(e.message, 'error')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center', color: 'var(--text-3)' }}>Loading lobby...</div>
    </div>
  )
  if (!lobby) return null

  const me = lobby.players?.find(p => p.id === user?.id)
  const inLobby = !!me
  const isCreator = lobby.created_by === user?.id
  const isCaptain1 = lobby.captain1_id === user?.id
  const isCaptain2 = lobby.captain2_id === user?.id
  const isStaff = ['admin','developer'].includes(user?.role)
  const myTurn = (lobby.current_turn === 1 && isCaptain1) || (lobby.current_turn === 2 && isCaptain2) || isStaff

  const team1 = lobby.players?.filter(p => p.team === 1) || []
  const team2 = lobby.players?.filter(p => p.team === 2) || []
  const unassigned = lobby.players?.filter(p => p.team === 0) || []
  const canSubmit = ['moderator','admin','developer'].includes(user?.role) && matchId

  return (
    <div style={{ padding: '0 0 16px' }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 12
      }}>
        <button onClick={() => navigate('/lobbies')} style={{
          background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
          width: 34, height: 34, cursor: 'pointer', color: 'var(--text-1)', fontSize: 16,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
        }}>←</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.1rem', letterSpacing: 1, textTransform: 'uppercase' }}>
            {lobby.name}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <StatusBadge status={lobby.status} />
            {lobby.map && <span style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>🗺️ {lobby.map}</span>}
          </div>
        </div>
        {canSubmit && (
          <button className="btn-success" style={{ padding: '7px 12px', fontSize: '0.8rem' }}
            onClick={() => setShowSubmit(true)}>
            ✅ Result
          </button>
        )}
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Phase indicator */}
        {lobby.status === 'picking' && (
          <div style={{
            background: 'var(--bg-2)', borderRadius: 10, padding: '12px 16px',
            border: `1px solid ${myTurn ? 'var(--brand)' : 'var(--border)'}`,
            transition: 'border-color 0.3s'
          }}>
            <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1rem', letterSpacing: 1, marginBottom: 6, color: myTurn ? 'var(--brand)' : 'var(--text-2)' }}>
              {lobby.current_phase === 'ban' ? '🚫 MAP BAN PHASE' : '✅ MAP PICK PHASE'}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-3)' }}>
              {myTurn ? "⚡ Your turn!" : `Waiting for ${lobby.current_turn === 1 ? 'Team 1' : 'Team 2'} captain...`}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>
                Bans: {lobby.ban_count}/4 · Picks: {lobby.pick_count}/1
              </span>
            </div>
          </div>
        )}

        {/* Teams */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <TeamPanel
            label="TEAM 1" color="#3b82f6" players={team1}
            captain={lobby.captain1_id} currentUser={user}
            isTurn={lobby.current_turn === 1 && lobby.status === 'picking'}
          />
          <TeamPanel
            label="TEAM 2" color="#ef4444" players={team2}
            captain={lobby.captain2_id} currentUser={user}
            isTurn={lobby.current_turn === 2 && lobby.status === 'picking'}
          />
        </div>

        {/* Unassigned players */}
        {unassigned.length > 0 && (
          <div>
            <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, letterSpacing: 1, color: 'var(--text-3)', marginBottom: 8, textTransform: 'uppercase', fontSize: '0.85rem' }}>
              Unassigned ({unassigned.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {unassigned.map(p => {
                const canPick = lobby.status === 'picking' && myTurn && lobby.current_phase !== 'ban'
                const canSetCap2 = (isCreator || isStaff) && !lobby.captain2_id && lobby.status === 'waiting' && p.id !== user?.id
                return (
                  <div key={p.id} className="card" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Avatar username={p.username} color={p.avatar_color} size={32} role={p.role} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{p.username}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>{p.elo} ELO</div>
                    </div>
                    {canSetCap2 && (
                      <button className="btn-secondary" style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                        disabled={actionLoading}
                        onClick={() => action(() => api.post('/lobbies/set-captain2', { lobby_id: Number(id), player_id: p.id }))}>
                        👑 Cap2
                      </button>
                    )}
                    {canPick && (
                      <button className="btn-primary" style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                        disabled={actionLoading}
                        onClick={() => action(() => api.post('/lobbies/pick-player', { lobby_id: Number(id), player_id: p.id }))}>
                        + Pick
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Map pick/ban */}
        {(lobby.status === 'picking' || lobby.status === 'in_progress') && (
          <MapGrid
            lobby={lobby} myTurn={myTurn} actionLoading={actionLoading}
            onBan={(map) => action(() => api.post('/lobbies/ban-map', { lobby_id: Number(id), map_name: map }))}
            onPick={(map) => action(() => api.post('/lobbies/pick-map', { lobby_id: Number(id), map_name: map }))}
          />
        )}

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {!inLobby && lobby.status === 'waiting' && (
            <button className="btn-primary" style={{ padding: 14 }}
              disabled={actionLoading || user?.is_banned}
              onClick={() => action(() => api.post('/lobbies/join', { lobby_id: Number(id) }))}>
              🎮 Join Lobby
            </button>
          )}
          {inLobby && lobby.status === 'waiting' && !isCreator && (
            <button className="btn-secondary" style={{ padding: 14 }}
              disabled={actionLoading}
              onClick={() => action(() => api.post('/lobbies/leave', { lobby_id: Number(id) }))}>
              ← Leave
            </button>
          )}
          {(isCreator || isStaff) && lobby.status === 'waiting' && (
            <button className="btn-primary" style={{ padding: 14 }}
              disabled={actionLoading || lobby.players?.length < 2}
              onClick={() => action(() => api.post('/lobbies/start-picking', { lobby_id: Number(id) }))}>
              🎯 Start Pick/Ban Phase
            </button>
          )}
        </div>
      </div>

      {/* Submit result modal */}
      {showSubmit && matchId && (
        <SubmitResultModal
          matchId={matchId}
          onClose={() => setShowSubmit(false)}
          onDone={() => { setShowSubmit(false); load(); show('Result submitted! ELO updated.', 'success') }}
          show={show}
        />
      )}
      {el}
    </div>
  )
}

function TeamPanel({ label, color, players, captain, currentUser, isTurn }) {
  const slots = Array.from({ length: 5 })
  return (
    <div style={{
      background: 'var(--bg-2)', borderRadius: 10, padding: 10,
      border: `1px solid ${isTurn ? color : 'var(--border)'}`,
      transition: 'border-color 0.3s'
    }}>
      <div style={{
        fontFamily: 'Barlow Condensed', fontWeight: 800, color, fontSize: '0.9rem',
        letterSpacing: 2, marginBottom: 8, textTransform: 'uppercase',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        {label}
        {isTurn && <span style={{ fontSize: '0.7rem', background: color + '25', color, borderRadius: 4, padding: '2px 6px' }}>TURN</span>}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {slots.map((_, i) => {
          const p = players[i]
          if (!p) return (
            <div key={i} style={{
              height: 30, borderRadius: 6, border: '1px dashed var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>empty</span>
            </div>
          )
          return (
            <div key={p.id} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--bg-3)', borderRadius: 6, padding: '4px 8px'
            }}>
              <Avatar username={p.username} size={20} role={p.role} color={p.avatar_color} />
              <span style={{ fontSize: '0.78rem', fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {p.username}
              </span>
              {p.id === captain && <span style={{ fontSize: 12 }}>👑</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function MapGrid({ lobby, myTurn, actionLoading, onBan, onPick }) {
  const banned = lobby.banned_maps || []
  const picked = lobby.picked_maps || []
  const phase = lobby.current_phase

  return (
    <div>
      <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, letterSpacing: 1, color: 'var(--text-2)', marginBottom: 10, textTransform: 'uppercase', fontSize: '0.9rem' }}>
        {lobby.status === 'in_progress' ? '🗺️ Selected Map' : '🗺️ Map Pool'}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {MAPS_POOL.map(map => {
          const isBanned = banned.includes(map)
          const isPicked = picked.includes(map)
          const available = !isBanned && !isPicked
          const canAct = myTurn && available && lobby.status === 'picking' && !actionLoading

          return (
            <div key={map} style={{
              position: 'relative', borderRadius: 10, overflow: 'hidden',
              border: `2px solid ${isBanned ? '#ef4444' : isPicked ? '#10b981' : canAct ? 'transparent' : 'var(--border)'}`,
              opacity: isBanned ? 0.35 : 1,
              cursor: canAct ? 'pointer' : 'default',
              transition: 'all 0.2s',
              background: 'var(--bg-3)',
              aspectRatio: '1.4',
            }} onClick={() => {
              if (!canAct) return
              if (phase === 'ban') onBan(map)
              else onPick(map)
            }}>
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 4
              }}>
                <span style={{ fontSize: 22 }}>{MAP_ICONS[map] || '🗺️'}</span>
                <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.78rem', letterSpacing: 0.5, textAlign: 'center' }}>
                  {map}
                </span>
                {isBanned && <span style={{ fontSize: '0.65rem', color: '#ef4444', fontWeight: 700 }}>BANNED</span>}
                {isPicked && <span style={{ fontSize: '0.65rem', color: '#10b981', fontWeight: 700 }}>PICKED</span>}
                {canAct && (
                  <span style={{
                    fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                    color: phase === 'ban' ? '#ef4444' : '#10b981'
                  }}>
                    {phase === 'ban' ? '🚫 BAN' : '✅ PICK'}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SubmitResultModal({ matchId, onClose, onDone, show }) {
  const [winner, setWinner] = useState(1)
  const [s1, setS1] = useState('')
  const [s2, setS2] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    try {
      await api.post('/matches/submit-result', {
        match_id: matchId,
        winner,
        score_team1: parseInt(s1) || 0,
        score_team2: parseInt(s2) || 0,
      })
      onDone()
    } catch (e) {
      show(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="Submit Match Result" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-3)', marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>WINNER</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[1, 2].map(t => (
              <button key={t} onClick={() => setWinner(t)} style={{
                flex: 1, padding: '12px 0',
                background: winner === t ? (t === 1 ? '#3b82f6' : '#ef4444') : 'var(--bg-3)',
                border: `1px solid ${winner === t ? (t === 1 ? '#3b82f6' : '#ef4444') : 'var(--border)'}`,
                borderRadius: 8, cursor: 'pointer', color: 'white',
                fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '1rem', letterSpacing: 1
              }}>
                TEAM {t} WINS
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: '0.78rem', color: '#3b82f6', fontWeight: 700, letterSpacing: 1 }}>TEAM 1 SCORE</label>
            <input className="input" style={{ padding: '10px 14px', textAlign: 'center' }}
              type="number" value={s1} onChange={e => setS1(e.target.value)} placeholder="13" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', paddingTop: 24, color: 'var(--text-3)', fontWeight: 700 }}>:</div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: '0.78rem', color: '#ef4444', fontWeight: 700, letterSpacing: 1 }}>TEAM 2 SCORE</label>
            <input className="input" style={{ padding: '10px 14px', textAlign: 'center' }}
              type="number" value={s2} onChange={e => setS2(e.target.value)} placeholder="8" />
          </div>
        </div>
        <button className="btn-primary" style={{ padding: 14 }} disabled={loading} onClick={submit}>
          {loading ? '...' : '✅ CONFIRM RESULT'}
        </button>
      </div>
    </Modal>
  )
}
