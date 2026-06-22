/**
 * Axios instance wired to the FastAPI backend.
 *
 * Request interceptor  — attaches the stored access token as Bearer.
 * Response interceptor — on 401, attempts one silent token refresh using
 *                        the stored refresh token, then retries the original
 *                        request. If refresh fails, clears storage and
 *                        redirects to /login.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// ── Storage helpers ──────────────────────────────────────────────────────────
const TOKEN_KEY = 'notes_access_token'
const REFRESH_KEY = 'notes_refresh_token'

export const tokenStorage = {
  getAccess: ()  => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access, refresh) => {
    localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

// ── Request interceptor — attach access token ────────────────────────────────
api.interceptors.request.use(config => {
  const token = tokenStorage.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor — silent refresh on 401 ────────────────────────────
let _isRefreshing = false
let _pendingQueue = []

const processPending = (error, token = null) => {
  _pendingQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token)
  )
  _pendingQueue = []
}

api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config

    // Only attempt refresh on 401, and only once per request
    if (err.response?.status !== 401 || original._retried) {
      return Promise.reject(err)
    }

    // Don't attempt refresh for the auth endpoints themselves
    if (original.url?.includes('/auth/')) {
      return Promise.reject(err)
    }

    original._retried = true

    if (_isRefreshing) {
      return new Promise((resolve, reject) => {
        _pendingQueue.push({ resolve, reject })
      }).then(token => {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      })
    }

    _isRefreshing = true
    const refreshToken = tokenStorage.getRefresh()

    if (!refreshToken) {
      tokenStorage.clear()
      window.location.href = '/login'
      return Promise.reject(err)
    }

    try {
      const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      })
      tokenStorage.set(data.access_token, data.refresh_token)
      processPending(null, data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      return api(original)
    } catch (refreshErr) {
      processPending(refreshErr)
      tokenStorage.clear()
      window.location.href = '/login'
      return Promise.reject(refreshErr)
    } finally {
      _isRefreshing = false
    }
  }
)

export default api
