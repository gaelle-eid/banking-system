import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../lib/api'

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
  const [registered, setRegistered] = useState(false)
  const [newUserId, setNewUserId] = useState(null)
  const [idPhoto, setIdPhoto] = useState(null)
  const [uploadStatus, setUploadStatus] = useState('') // '', 'uploading', 'done', 'skipped'
  const [otpSent, setOtpSent] = useState(false)
  const [otpValue, setOtpValue] = useState('')
  const [otpStatus, setOtpStatus] = useState('') // '', 'sending', 'sent', 'verifying', 'done', 'skipped'
  const { register } = useAuth()

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await register(form)
      setNewUserId(user.id)
      setRegistered(true)
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

  async function handlePhotoUpload() {
    if (!idPhoto || !newUserId) return
    setUploadStatus('uploading')
    const formData = new FormData()
    formData.append('file', idPhoto)
    try {
      await api.post(`/auth/${newUserId}/upload-id-photo`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUploadStatus('done')
    } catch (err) {
      setUploadStatus('')
      setError(err.response?.data?.detail || 'Photo upload failed')
    }
  }

  async function handleSendOtp() {
    setOtpStatus('sending')
    setError('')
    try {
      await api.post(`/auth/${newUserId}/send-phone-otp`)
      setOtpSent(true)
      setOtpStatus('sent')
    } catch (err) {
      setOtpStatus('')
      setError(err.response?.data?.detail || 'Could not send code')
    }
  }

  async function handleVerifyOtp() {
    setOtpStatus('verifying')
    setError('')
    try {
      await api.post(`/auth/${newUserId}/verify-phone-otp`, { otp: otpValue })
      setOtpStatus('done')
    } catch (err) {
      setOtpStatus('sent')
      setError(err.response?.data?.detail || 'Incorrect code')
    }
  }

  const inputClass = "w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-crimson-600"
  const labelClass = "block text-sm font-medium text-ink-950 mb-1"

  if (registered) {
    const idStepDone = uploadStatus === 'done' || uploadStatus === 'skipped'
    const phoneStepDone = otpStatus === 'done' || otpStatus === 'skipped'

    if (!idStepDone) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
          <div className="w-full max-w-sm text-center">
            <div className="w-12 h-12 bg-crimson-100 text-crimson-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">🪪</div>
            <h1 className="font-display text-xl font-semibold text-ink-950 mb-2">Verify your identity</h1>
            <p className="text-stone-500 text-sm mb-6">
              Upload a clear photo of your national ID or passport. This helps us verify your identity before activating your account.
            </p>
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={(e) => setIdPhoto(e.target.files[0])}
              className="mb-4 text-sm w-full"
            />
            {error && <p className="text-crimson-600 text-sm mb-4">{error}</p>}
            <div className="flex gap-2">
              <button
                onClick={handlePhotoUpload}
                disabled={!idPhoto || uploadStatus === 'uploading'}
                className="flex-1 bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-800 transition disabled:opacity-50"
              >
                {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload photo'}
              </button>
              <button
                onClick={() => setUploadStatus('skipped')}
                className="px-4 py-2.5 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-white transition"
              >
                Skip for now
              </button>
            </div>
          </div>
        </div>
      )
    }

    if (!phoneStepDone) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
          <div className="w-full max-w-sm text-center">
            <div className="w-12 h-12 bg-crimson-100 text-crimson-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">📱</div>
            <h1 className="font-display text-xl font-semibold text-ink-950 mb-2">Verify your phone</h1>
            <p className="text-stone-500 text-sm mb-6">
              {!otpSent
                ? <>We'll send a verification code for <strong>{form.phone}</strong> to your email.</>
                : 'Enter the 6-digit code we sent to your email.'}
            </p>

            {error && <p className="text-crimson-600 text-sm mb-4">{error}</p>}

            {!otpSent ? (
              <div className="flex gap-2">
                <button
                  onClick={handleSendOtp}
                  disabled={otpStatus === 'sending'}
                  className="flex-1 bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-800 transition disabled:opacity-50"
                >
                  {otpStatus === 'sending' ? 'Sending...' : 'Send code'}
                </button>
                <button
                  onClick={() => setOtpStatus('skipped')}
                  className="px-4 py-2.5 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-white transition"
                >
                  Skip for now
                </button>
              </div>
            ) : (
              <>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  value={otpValue}
                  onChange={(e) => setOtpValue(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg text-center text-lg font-mono tracking-[0.3em] mb-4"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleVerifyOtp}
                    disabled={otpValue.length !== 6 || otpStatus === 'verifying'}
                    className="flex-1 bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-800 transition disabled:opacity-50"
                  >
                    {otpStatus === 'verifying' ? 'Verifying...' : 'Verify'}
                  </button>
                  <button
                    onClick={() => setOtpStatus('skipped')}
                    className="px-4 py-2.5 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-white transition"
                  >
                    Skip
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4">
        <div className="w-full max-w-sm text-center">
          <div className="w-12 h-12 bg-crimson-100 text-crimson-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">✉</div>
          <h1 className="font-display text-xl font-semibold text-ink-950 mb-2">Check your email</h1>
          <p className="text-stone-500 text-sm mb-6">
            We've sent a verification link to <strong>{form.email}</strong>. Click it to activate your account, then come back and log in.
          </p>
          <Link to="/login" className="text-crimson-600 text-sm font-medium">Back to login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="w-9 h-9 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm text-white mb-6">B</div>
        <h1 className="font-display text-2xl font-semibold text-ink-950 mb-1">Create your account</h1>
        <p className="text-stone-500 text-sm mb-8">Start banking with us.</p>

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
            <p className="text-xs text-stone-500 mt-1">At least 8 characters, with uppercase, lowercase, a number, and a symbol.</p>
          </div>

          <label className="flex items-start gap-2 text-sm text-stone-500">
            <input
              type="checkbox"
              required
              checked={form.accepted_terms}
              onChange={(e) => update('accepted_terms', e.target.checked)}
              className="mt-0.5 accent-crimson-600"
            />
            I agree to the Terms and Conditions and Privacy Policy.
          </label>

          {error && <p className="text-crimson-600 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-ink-950 text-white py-2.5 rounded-lg font-medium hover:bg-ink-800 transition disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-sm text-stone-500 mt-6">
          Already have an account? <Link to="/login" className="text-crimson-600 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}