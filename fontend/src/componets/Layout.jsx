import React from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useStore } from '../store'

const NAV = [
  { path: '/', icon: '🏠', label: 'Home' },
  { path: '/lobbies', icon: '🎮', label: 'Lobbies' },
  { path: '/leaderboard', icon: '🏆', label: 'Top' },
  { path: '/profile', icon: '👤', label: 'Profile' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useStore()

  const navItems = [...NAV]
  if (user && ['moderator', 'admin', 'developer'].includes(user.role)) {
    navItems.push({ path: '/admin', icon: '🛡️', label: 'Admin' })
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', paddingBottom: 65 }}>
      <div style={{ flex: 1 }}>
        <Outlet />
      </div>
      <nav className="nav-bar">
        {navItems.map(item => {
          const active = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <button
              key={item.path}
              className={`nav-item ${active ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
              style={{ background: 'none', border: 'none' }}
            >
              <span style={{ fontSize: 20 }}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
