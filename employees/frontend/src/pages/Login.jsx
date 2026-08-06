import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-9 h-9 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm text-white">B</div>
          <div>
            <p className="font-display text-sm font-semibold leading-none text-steel-900">Banking System</p>
            <p className="text-xs text-slate-500 mt-0.5">Employee Portal</p>
          </div>
        </div>

        <h1 className="font-display text-2xl font-semibold text-steel-900 mb-1">Staff sign in</h1>
        <p className="text-slate-500 text-sm mb-8">Access is restricted to bank employees and administrators.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-steel-900 mb-1">Work email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-crimson-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-steel-900 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-crimson-600"
            />
          </div>

          {error && <p className="text-crimson-600 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-steel-900 text-white py-2.5 rounded-lg font-medium hover:bg-steel-800 transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-xs text-slate-500 mt-6 flex items-center gap-1.5">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <rect x="5" y="11" width="14" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M8 11V7a4 4 0 118 0v4" stroke="currentColor" strokeWidth="1.8"/>
          </svg>
          Internal use only · Access is logged and monitored
        </p>
      </div>
    </div>
  )
}