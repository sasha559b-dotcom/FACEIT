import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from './api'

export const useStore = create(
  persist(
    (set, get) => ({
      user: null,
      initData: null,
      telegramId: null,

      setUser: (user) => set({ user }),
      setInitData: (initData) => set({ initData }),
      setTelegramId: (id) => set({ telegramId: String(id) }),

      login: async (initData, telegramId) => {
        try {
          const res = await api.post('/auth/login', { init_data: initData || String(telegramId) })
          if (res.data.registered) {
            set({ user: res.data.user })
            return { registered: true, user: res.data.user }
          }
          return { registered: false }
        } catch (e) {
          return { registered: false, error: e.message }
        }
      },

      register: async (username, gameId, initData, telegramId) => {
        const res = await api.post('/auth/register', {
          username,
          game_id: gameId,
          init_data: initData || String(telegramId),
        })
        if (res.data.success) {
          set({ user: res.data.user })
        }
        return res.data
      },

      refreshUser: async () => {
        const state = get()
        if (!state.user) return
        try {
          const res = await api.get(`/users/${state.user.id}`)
          set({ user: res.data })
        } catch (e) {}
      },

      logout: () => set({ user: null }),
    }),
    {
      name: 'faceit-tg-store',
      partialize: (state) => ({ user: state.user, telegramId: state.telegramId }),
    }
  )
)
