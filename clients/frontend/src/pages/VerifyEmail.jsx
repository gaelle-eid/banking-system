import { useState, useEffect, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import api from '../lib/api'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState('loading') // loading | success | error
  const [message, setMessage] = useState('')
  const calledRef = useRef(false)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token found in the link.')
      return
    }
    if (calledRef.current) return
    calledRef.current = true

    api.get(`/auth/verify?token=${token}`)
      .then((res) => {
        setStatus('success')
        setMessage(res.data.message)
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Verification failed.')
      })
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
      <div className="w-full max-w-sm text-center">
        {status === 'loading' && (
          <p className="text-slate-600">Verifying your email...</p>
        )}
        {status === 'success' && (
          <>
            <div className="w-12 h-12 bg-teal-500/15 text-teal-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">✓</div>
            <h1 className="font-display text-xl font-semibold text-ink-900 mb-2">Email verified</h1>
            <p className="text-slate-600 text-sm mb-6">{message}</p>
            <Link to="/login" className="inline-block bg-ink-900 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-ink-800 transition">
              Go to login
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="w-12 h-12 bg-coral-500/15 text-coral-500 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">✕</div>
            <h1 className="font-display text-xl font-semibold text-ink-900 mb-2">Verification failed</h1>
            <p className="text-slate-600 text-sm mb-6">{message}</p>
            <Link to="/login" className="inline-block text-teal-600 text-sm font-medium">Back to login</Link>
          </>
        )}
      </div>
    </div>
  )
}