import { createContext, useContext, useState, useEffect } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('employee_access_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem('employee_access_token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('employee_access_token', res.data.access_token)
    const meRes = await api.get('/auth/me')
    if (meRes.data.role !== 'employee' && meRes.data.role !== 'admin') {
      localStorage.removeItem('employee_access_token')
      throw { response: { data: { detail: 'This portal is for bank employees only.' } } }
    }
    setUser(meRes.data)
  }

  function logout() {
    localStorage.removeItem('employee_access_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
