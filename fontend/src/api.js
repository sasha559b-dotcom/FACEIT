import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
})

// Attach Telegram auth headers to every request
api.interceptors.request.use((config) => {
  try {
    const stored = JSON.parse(localStorage.getItem('faceit-tg-store') || '{}')
    const telegramId = stored?.state?.telegramId
    const initData = window.Telegram?.WebApp?.initData

    if (initData) {
      config.headers['x-init-data'] = initData
    }
    if (telegramId) {
      config.headers['x-telegram-id'] = String(telegramId)
    }
  } catch (e) {}
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(msg))
  }
)

export default api
