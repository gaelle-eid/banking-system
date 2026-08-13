import { useState } from 'react'
import api from '../lib/api'
import { useToast } from '../context/ToastContext'

export default function PhoneTransferForm({ accountId, onSuccess }) {
  const [phone, setPhone] = useState('')
  const [amount, setAmount] = useState('')
  const [stage, setStage] = useState('form') // 'form' | 'otp'
  const [verificationId, setVerificationId] = useState(null)
  const [recipientName, setRecipientName] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { showToast } = useToast()

  async function handleInitiate(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/transactions/phone-transfer/initiate', {
        from_account_id: accountId,
        to_phone: phone,
        amount: parseFloat(amount),
      })
      setVerificationId(res.data.verification_id)
      setRecipientName(res.data.recipient_name)
      setStage('otp')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start transfer')
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/transactions/phone-transfer/confirm', {
        verification_id: verificationId,
        otp,
      })
      showToast('Transfer completed')
      setPhone('')
      setAmount('')
      setOtp('')
      setStage('form')
      onSuccess?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed')
    } finally {
      setLoading(false)
    }
  }

  if (stage === 'otp') {
    return (
      <form onSubmit={handleConfirm} className="bg-white rounded-xl p-4 border border-stone-300/40">
        <h3 className="font-medium text-sm mb-1 text-ink-950">Enter code</h3>
        <p className="text-xs text-stone-500 mb-1">
          Sending {amount} {' '}to <span className="font-medium text-ink-950">{recipientName}</span> ({phone})
        </p>
        <p className="text-xs text-stone-500 mb-3">We emailed you a 6-digit verification code.</p>
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          required
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
          placeholder="000000"
          className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2 font-mono text-center tracking-[0.3em]"
        />
        {error && <p className="text-crimson-600 text-xs mb-2">{error}</p>}
        <div className="flex gap-2">
          <button disabled={loading || otp.length !== 6} className="flex-1 bg-crimson-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50">
            {loading ? 'Verifying...' : 'Confirm'}
          </button>
          <button
            type="button"
            onClick={() => { setStage('form'); setOtp(''); setError('') }}
            className="px-3 py-2 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-white transition"
          >
            Cancel
          </button>
        </div>
      </form>
    )
  }

  return (
    <form onSubmit={handleInitiate} className="bg-white rounded-xl p-4 border border-stone-300/40">
      <h3 className="font-medium text-sm mb-3 text-ink-950">Send by phone number</h3>
      <input
        type="tel"
        required
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="+96170123456"
        className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2"
      />
      <input
        type="number" step="0.01" min="0.01" required
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="Amount"
        className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2 font-mono"
      />
      {error && <p className="text-crimson-600 text-xs mb-2">{error}</p>}
      <button disabled={loading} className="w-full bg-crimson-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50">
        {loading ? 'Sending...' : 'Send code & continue'}
      </button>
    </form>
  )
}