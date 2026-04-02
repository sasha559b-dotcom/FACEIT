import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useStore } from './store'
import RegisterPage from './pages/RegisterPage'
import HomePage from './pages/HomePage'
import LobbyPage from './pages/LobbyPage'
import LobbyListPage from './pages/LobbyListPage'
import ProfilePage from './pages/ProfilePage'
import LeaderboardPage from './pages/LeaderboardPage'
import AdminPage from './pages/AdminPage'
import MatchPage from './pages/MatchPage'
import Layout from './components/Layout'

export default function App() {
  const { user, login, setInitData, setTelegramId } = useStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
      tg.setHeaderColor('#0F0F13')
      tg.setBackgroundColor('#0F0F13')
    }

    const initData = tg?.initData || ''
    const tgUser = tg?.initDataUnsafe?.user
    const telegramId = tgUser?.id || null

    setInitData(initData)
    if (telegramId) setTelegramId(telegramId)

    // Auto-login
    const idToUse = telegramId || (initData ? undefined : null)
    if (idToUse || initData) {
      login(initData, idToUse).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  if (loading) return <Splash />

  if (!user) return (
    <BrowserRouter>
      <Routes>
        <Route path="*" element={<RegisterPage />} />
      </Routes>
    </BrowserRouter>
  )

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/lobbies" element={<LobbyListPage />} />
          <Route path="/lobby/:id" element={<LobbyPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/profile/:id" element={<ProfilePage />} />
          <Route path="/match/:id" element={<MatchPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

function Splash() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16,
      background: 'var(--bg-0)'
    }}>
      <div style={{ fontSize: 48 }}>⚡</div>
      <div style={{
        fontFamily: 'Barlow Condensed', fontSize: 28, fontWeight: 800,
        color: 'var(--brand)', letterSpacing: 4, textTransform: 'uppercase'
      }}>FaceitTG</div>
      <div style={{ color: 'var(--text-3)', fontSize: 14 }}>Loading...</div>
      <div style={{
        width: 120, height: 3, background: 'var(--bg-3)',
        borderRadius: 2, overflow: 'hidden', marginTop: 8
      }}>
        <div style={{
          height: '100%', background: 'var(--brand)',
          animation: 'shimmer 1s infinite',
          backgroundImage: 'linear-gradient(90deg, var(--brand) 0%, #ff9500 50%, var(--brand) 100%)',
          backgroundSize: '200% 100%'
        }} />
      </div>
    </div>
  )
}
