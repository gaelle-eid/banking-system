import { createContext, useContext, useState, useEffect } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem('access_token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('access_token', res.data.access_token)
    const meRes = await api.get('/auth/me')
    setUser(meRes.data)
  }

  async function register(formData) {
    const res = await api.post('/auth/register', { ...formData, role: 'client' })
    return res.data
  }

  function logout() {
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}