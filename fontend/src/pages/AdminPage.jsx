import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { Avatar, RoleBadge, Modal, useToast } from '../components/UI'
import api from '../api'

const ROLE_HIERARCHY = { player: 0, moderator: 1, admin: 2, developer: 3 }

export default function AdminPage() {
  const { user } = useStore()
  const navigate = useNavigate()

  if (!user || !['moderator', 'admin', 'developer'].includes(user.role)) {
    navigate('/')
    return null
  }

  const tabs = [
    { id: 'users', label: '👥 Users', minRole: 'moderator' },
    { id: 'stats', label: '📊 Stats', minRole: 'moderator' },
    { id: 'audit', label: '📋 Audit', minRole: 'admin' },
  ].filter(t => ROLE_HIERARCHY[user.role] >= ROLE_HIERARCHY[t.minRole])

  const [tab, setTab] = useState(tabs[0]?.id)

  return (
    <div style={{ padding: '16px 16px 0' }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.4rem', letterSpacing: 2, textTransform: 'uppercase' }}>
          🛡️ Admin Panel
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
          <RoleBadge role={user.role} />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>{user.username}</span>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 6, marginBottom: 16, background: 'var(--bg-2)',
        borderRadius: 10, padding: 4
      }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            flex: 1, padding: '8px 4px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: tab === t.id ? 'var(--brand)' : 'transparent',
            color: tab === t.id ? 'white' : 'var(--text-3)',
            fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.82rem', letterSpacing: 0.5
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'users' && <UsersTab currentUser={user} />}
      {tab === 'stats' && <StatsTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  )
}

function UsersTab({ currentUser }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const { show, el } = useToast()

  const load = () => {
    api.get('/admin/users').then(r => setUsers(r.data)).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const filtered = users.filter(u =>
    u.username.toLowerCase().includes(search.toLowerCase()) ||
    u.game_id.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <input className="input" style={{ padding: '10px 14px', marginBottom: 12 }}
        placeholder="🔍 Search players..."
        value={search} onChange={e => setSearch(e.target.value)} />

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {filtered.map(u => (
            <div key={u.id} className="card card-hover" style={{
              padding: '10px 14px', cursor: 'pointer',
              opacity: u.is_banned ? 0.6 : 1,
            }} onClick={() => setSelected(u)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Avatar username={u.username} color={u.avatar_color} size={36} role={u.role} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{u.username}</span>
                    {u.is_banned && <span style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 700 }}>BANNED</span>}
                    {u.is_muted && <span style={{ fontSize: '0.7rem', color: '#f59e0b', fontWeight: 700 }}>MUTED</span>}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
                    {u.elo} ELO · {u.wins}W/{u.losses}L · <span className={`role-${u.role}`}>{u.role}</span>
                  </div>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>›</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <UserActionModal
          target={selected}
          currentUser={currentUser}
          onClose={() => { setSelected(null); load() }}
          show={show}
        />
      )}
      {el}
    </div>
  )
}

function UserActionModal({ target, currentUser, onClose, show }) {
  const [reason, setReason] = useState('')
  const [elo, setElo] = useState(target.elo)
  const [role, setRole] = useState(target.role)
  const [loading, setLoading] = useState(false)

  const myLevel = ROLE_HIERARCHY[currentUser.role] || 0
  const targetLevel = ROLE_HIERARCHY[target.role] || 0
  const canAct = myLevel > targetLevel

  const act = async (fn, successMsg) => {
    setLoading(true)
    try {
      await fn()
      show(successMsg, 'success')
      onClose()
    } catch (e) {
      show(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const isMod = myLevel >= 1
  const isAdmin = myLevel >= 2
  const isDev = myLevel >= 3

  return (
    <Modal title={`Manage: ${target.username}`} onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* User info */}
        <div style={{
          background: 'var(--bg-2)', borderRadius: 10, padding: '12px 14px',
          display: 'flex', alignItems: 'center', gap: 12
        }}>
          <Avatar username={target.username} color={target.avatar_color} size={44} role={target.role} />
          <div>
            <div style={{ fontWeight: 700 }}>{target.username}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>{target.elo} ELO · <span className={`role-${target.role}`}>{target.role}</span></div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-3)' }}>🎮 {target.game_id}</div>
          </div>
        </div>

        {!canAct && (
          <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '10px 14px', color: '#ef4444', fontSize: '0.85rem' }}>
            ⛔ You cannot manage users with equal or higher role
          </div>
        )}

        {/* Reason input */}
        {canAct && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>REASON (for ban/mute/elo)</label>
            <input className="input" style={{ padding: '10px 14px' }}
              placeholder="Enter reason..."
              value={reason} onChange={e => setReason(e.target.value)} />
          </div>
        )}

        {/* Moderator actions */}
        {isMod && canAct && (
          <div>
            <div style={{ fontSize: '0.8rem', color: '#3b82f6', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>MODERATOR ACTIONS</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <button className={target.is_muted ? 'btn-success' : 'btn-danger'} style={{ padding: '10px 0' }}
                disabled={loading}
                onClick={() => act(
                  () => api.post(target.is_muted ? '/admin/unmute' : '/admin/mute', { user_id: target.id, reason }),
                  target.is_muted ? 'User unmuted' : 'User muted'
                )}>
                {target.is_muted ? '🔊 Unmute' : '🔇 Mute'}
              </button>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input className="input" style={{ padding: '8px 10px', textAlign: 'center' }}
                  type="number" placeholder="±ELO" value=""
                  onChange={e => {}} />
              </div>
            </div>

            {/* Give ELO */}
            <div style={{ marginTop: 10 }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1 }}>GIVE/TAKE ELO (relative)</label>
              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                {[-50, -25, +25, +50].map(v => (
                  <button key={v} className={v > 0 ? 'btn-success' : 'btn-danger'} style={{ flex: 1, padding: '8px 0', fontSize: '0.8rem' }}
                    disabled={loading}
                    onClick={() => act(
                      () => api.post('/admin/give-elo', { user_id: target.id, elo: v, reason: reason || `${v > 0 ? '+' : ''}${v} ELO by ${currentUser.username}` }),
                      `ELO ${v > 0 ? '+' : ''}${v} applied`
                    )}>
                    {v > 0 ? '+' : ''}{v}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Admin actions */}
        {isAdmin && canAct && (
          <div>
            <div style={{ fontSize: '0.8rem', color: '#8b5cf6', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>ADMIN ACTIONS</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <button className={target.is_banned ? 'btn-success' : 'btn-danger'} style={{ padding: '10px 0' }}
                disabled={loading}
                onClick={() => act(
                  () => api.post(target.is_banned ? '/admin/unban' : '/admin/ban', { user_id: target.id, reason }),
                  target.is_banned ? 'User unbanned' : 'User banned'
                )}>
                {target.is_banned ? '✅ Unban' : '🚫 Ban'}
              </button>
            </div>
          </div>
        )}

        {/* Developer actions */}
        {isDev && canAct && (
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--brand)', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>DEVELOPER ACTIONS</div>

            {/* Set exact ELO */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input className="input" style={{ padding: '10px 14px', flex: 1 }}
                type="number" placeholder="Set exact ELO"
                value={elo} onChange={e => setElo(Number(e.target.value))} />
              <button className="btn-primary" style={{ padding: '0 16px', whiteSpace: 'nowrap' }}
                disabled={loading}
                onClick={() => act(
                  () => api.post('/admin/set-elo', { user_id: target.id, elo: Number(elo), reason }),
                  `ELO set to ${elo}`
                )}>
                Set ELO
              </button>
            </div>

            {/* Set role */}
            <div style={{ display: 'flex', gap: 8 }}>
              <select className="input" style={{ padding: '10px 14px', flex: 1 }}
                value={role} onChange={e => setRole(e.target.value)}>
                <option value="player">Player</option>
                <option value="moderator">Moderator</option>
                <option value="admin">Admin</option>
                <option value="developer">Developer</option>
              </select>
              <button className="btn-primary" style={{ padding: '0 16px' }}
                disabled={loading}
                onClick={() => act(
                  () => api.post('/admin/set-role', { user_id: target.id, role }),
                  `Role set to ${role}`
                )}>
                Set Role
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

function StatsTab() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    api.get('/admin/stats').then(r => setStats(r.data))
  }, [])

  if (!stats) return <div className="skeleton" style={{ height: 200, borderRadius: 12 }} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
        {[
          { label: 'Total Players', value: stats.total_users, icon: '👥', color: '#6366f1' },
          { label: 'Active Lobbies', value: stats.active_lobbies, icon: '🎮', color: '#10b981' },
          { label: 'Total Matches', value: stats.total_matches, icon: '⚔️', color: '#f59e0b' },
          { label: 'Banned Users', value: stats.banned_users, icon: '🚫', color: '#ef4444' },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>{s.icon}</div>
            <div style={{ fontFamily: 'Barlow Condensed', fontWeight: 900, fontSize: '2rem', color: s.color }}>
              {s.value}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
      {stats.top_player && (
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-3)', fontWeight: 700, letterSpacing: 1, marginBottom: 8, textTransform: 'uppercase' }}>
            🏆 Top Player
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.2rem' }}>
              {stats.top_player.username}
            </span>
            <span style={{ fontFamily: 'Barlow Condensed', fontWeight: 800, fontSize: '1.2rem', color: 'var(--brand)' }}>
              {stats.top_player.elo} ELO
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function AuditTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/admin/audit-log').then(r => setLogs(r.data)).finally(() => setLoading(false))
  }, [])

  const actionColors = {
    ban: '#ef4444', unban: '#10b981', mute: '#f59e0b', unmute: '#10b981',
    give_elo: '#6366f1', set_elo: 'var(--brand)', set_role: '#8b5cf6',
    submit_result: '#06b6d4', add_map: '#10b981'
  }

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 56 }} />)}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {logs.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text-3)', padding: '32px 0' }}>No audit logs yet</div>
      )}
      {logs.map(log => (
        <div key={log.id} className="card" style={{ padding: '10px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{
              color: actionColors[log.action] || 'var(--text-2)',
              fontFamily: 'Barlow Condensed', fontWeight: 700, fontSize: '0.85rem', letterSpacing: 1, textTransform: 'uppercase'
            }}>
              {log.action.replace(/_/g, ' ')}
            </span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>
              {new Date(log.created_at).toLocaleString('en', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>
            <span style={{ color: 'var(--text-2)' }}>{log.admin_name || '?'}</span>
            {log.target_name && <> → <span style={{ color: 'var(--text-2)' }}>{log.target_name}</span></>}
            {log.details && <div style={{ marginTop: 2, fontSize: '0.75rem' }}>{log.details}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}
