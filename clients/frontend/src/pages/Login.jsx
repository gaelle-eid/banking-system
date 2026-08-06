import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
      <div className="w-full max-w-sm">
        <div className="w-9 h-9 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm text-white mb-6">B</div>
        <h1 className="font-display text-2xl font-semibold text-ink-950 mb-1">Welcome back</h1>
        <p className="text-stone-500 text-sm mb-8">Sign in to manage your accounts.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-950 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-crimson-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-950 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-crimson-600"
            />
          </div>

          {error && <p className="text-crimson-600 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ink-950 text-white py-2.5 rounded-lg font-medium hover:bg-ink-800 transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-sm text-stone-500 mt-6">
          Don't have an account? <Link to="/register" className="text-crimson-600 font-medium">Register</Link>
        </p>
      </div>
    </div>
  )
}