import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/auth'
import { tokenStorage } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true) // true until initial /me check resolves

  // On mount, if tokens exist attempt to restore the session
  useEffect(() => {
    const restore = async () => {
      const token = tokenStorage.getAccess()
      if (!token) { setLoading(false); return }
      try {
        const { data } = await authApi.me()
        setUser(data)
      } catch {
        tokenStorage.clear()
      } finally {
        setLoading(false)
      }
    }
    restore()
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await authApi.login(email, password)
    tokenStorage.set(data.access_token, data.refresh_token)
    const { data: me } = await authApi.me()
    setUser(me)
    return me
  }, [])

  const register = useCallback(async (email, password, fullName) => {
    await authApi.register(email, password, fullName)
    return login(email, password)
  }, [login])

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    try {
      if (refresh) await authApi.logout(refresh)
    } catch { /* already invalid — proceed anyway */ }
    tokenStorage.clear()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
