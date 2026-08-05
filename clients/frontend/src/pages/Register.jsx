import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    address: '',
    national_id: '',
    password: '',
    accepted_terms: false,
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      navigate('/')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(' / '))
      } else {
        setError(detail || 'Registration failed')
      }
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
  const labelClass = "block text-sm font-medium text-ink-900 mb-1"

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4 py-12">
      <div className="w-full max-w-md">
        <h1 className="font-display text-2xl font-semibold text-ink-900 mb-1">Create your account</h1>
        <p className="text-slate-600 text-sm mb-8">Start banking with us.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Full name</label>
            <input type="text" required value={form.full_name} onChange={(e) => update('full_name', e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Phone</label>
              <input type="tel" required placeholder="+96170123456" value={form.phone} onChange={(e) => update('phone', e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Date of birth</label>
              <input type="date" required value={form.date_of_birth} onChange={(e) => update('date_of_birth', e.target.value)} className={inputClass} />
            </div>
          </div>
          <div>
            <label className={labelClass}>Address</label>
            <input type="text" required placeholder="123 Main St, Beirut, Lebanon" value={form.address} onChange={(e) => update('address', e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>National ID</label>
            <input type="text" required value={form.national_id} onChange={(e) => update('national_id', e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Password</label>
            <input type="password" required value={form.password} onChange={(e) => update('password', e.target.value)} className={inputClass} />
            <p className="text-xs text-slate-400 mt-1">At least 8 characters, with uppercase, lowercase, a number, and a symbol.</p>
          </div>

          <label className="flex items-start gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              required
              checked={form.accepted_terms}
              onChange={(e) => update('accepted_terms', e.target.checked)}
              className="mt-0.5"
            />
            I agree to the Terms and Conditions and Privacy Policy.
          </label>

          {error && <p className="text-coral-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ink-900 text-white py-2.5 rounded-lg font-medium hover:bg-ink-800 transition disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-sm text-slate-600 mt-6">
          Already have an account? <Link to="/login" className="text-teal-600 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}