import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'

const statusLabel = {
  pending_verification: { text: 'Pending verification', className: 'bg-stone-300/30 text-stone-500' },
  verified: { text: 'Verified', className: 'bg-ink-950/10 text-ink-950' },
  failed: { text: 'Failed', className: 'bg-crimson-600/10 text-crimson-600' },
}

export default function LinkedAccounts() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [bankName, setBankName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const [justLinked, setJustLinked] = useState(null) // { id, demo_micro_deposits }
  const [verifyInputs, setVerifyInputs] = useState({}) // { [sourceId]: { amount_1, amount_2 } }
  const [verifying, setVerifying] = useState(null)
  const { showToast } = useToast()

  async function loadSources() {
    setLoading(true)
    try {
      const res = await api.get('/funding-sources')
      setSources(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSources()
  }, [])

  async function handleLink(e) {
    e.preventDefault()
    setError('')
    setAdding(true)
    try {
      const res = await api.post('/funding-sources', { bank_name: bankName, account_number: accountNumber })
      setJustLinked(res.data)
      setBankName('')
      setAccountNumber('')
      setShowAdd(false)
      await loadSources()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not link this account')
    } finally {
      setAdding(false)
    }
  }

  async function handleVerify(sourceId) {
    const inputs = verifyInputs[sourceId] || {}
    setVerifying(sourceId)
    try {
      await api.post(`/funding-sources/${sourceId}/verify`, {
        amount_1: parseFloat(inputs.amount_1) || 0,
        amount_2: parseFloat(inputs.amount_2) || 0,
      })
      showToast('Funding source verified')
      if (justLinked?.id === sourceId) setJustLinked(null)
      await loadSources()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Verification failed', 'error')
      await loadSources()
    } finally {
      setVerifying(null)
    }
  }

  async function handleRemove(sourceId) {
    try {
      await api.delete(`/funding-sources/${sourceId}`)
      if (justLinked?.id === sourceId) setJustLinked(null)
      showToast('Removed')
      await loadSources()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not remove', 'error')
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950">Linked Accounts</h1>
          <p className="text-stone-500 text-sm mt-1">
            External bank accounts you can deposit from. New accounts must be verified before use.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="px-3 py-1.5 bg-crimson-600 text-white rounded-lg text-xs font-medium hover:bg-crimson-700 transition"
        >
          + Link account
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleLink} className="bg-white rounded-xl p-5 border border-stone-300/40 mb-6 max-w-sm">
          <h3 className="font-medium text-sm text-ink-950 mb-3">Link a bank account</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Bank name</label>
              <input
                type="text" required value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                placeholder="e.g. BLOM Bank"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Account number</label>
              <input
                type="text" required minLength={4} value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder="e.g. 000123454521"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
          </div>
          {error && <p className="text-crimson-600 text-xs mt-2">{error}</p>}
          <div className="flex gap-2 mt-4">
            <button
              type="submit" disabled={adding}
              className="px-4 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-800 transition disabled:opacity-50"
            >
              {adding ? 'Linking...' : 'Link account'}
            </button>
            <button
              type="button" onClick={() => setShowAdd(false)}
              className="px-4 py-2 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-white transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {justLinked && (
        <div className="bg-white rounded-xl border border-crimson-600/40 p-4 mb-6 max-w-md">
          <p className="text-sm text-ink-950 mb-1 font-medium">
            {justLinked.bank_name} {justLinked.masked_account_number} linked - verify it now
          </p>
          <p className="text-xs text-stone-500 mb-3">
            In a real bank, these two small amounts would be sent to your external account and you'd
            check your statement there. Since this is a demo with no real external bank, here they are directly:{' '}
            <strong className="text-ink-950">${Number(justLinked.demo_micro_deposits[0]).toFixed(2)}</strong> and{' '}
            <strong className="text-ink-950">${Number(justLinked.demo_micro_deposits[1]).toFixed(2)}</strong>.
          </p>
        </div>
      )}

      {loading ? (
        <p className="text-stone-500 text-sm">Loading...</p>
      ) : sources.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-stone-300/40">
          <p className="text-stone-500">No linked accounts yet.</p>
          <p className="text-sm text-stone-500/70 mt-1">Link one above before you can make a deposit.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((s) => {
            const badge = statusLabel[s.status]
            const inputs = verifyInputs[s.id] || {}
            return (
              <div key={s.id} className="bg-white rounded-xl border border-stone-300/40 p-4">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium text-ink-950">{s.bank_name} {s.masked_account_number}</p>
                    <span className={`inline-block mt-1 text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full ${badge.className}`}>
                      {badge.text}
                    </span>
                  </div>
                  {s.status !== 'verified' && (
                    <button
                      onClick={() => handleRemove(s.id)}
                      className="text-xs text-crimson-600 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </div>

                {s.status === 'pending_verification' && (
                  <div className="flex gap-2 mt-3">
                    <input
                      type="number" step="0.01" min="0" max="0.99" placeholder="$0.00"
                      value={inputs.amount_1 || ''}
                      onChange={(e) => setVerifyInputs({ ...verifyInputs, [s.id]: { ...inputs, amount_1: e.target.value } })}
                      className="w-24 px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
                    />
                    <input
                      type="number" step="0.01" min="0" max="0.99" placeholder="$0.00"
                      value={inputs.amount_2 || ''}
                      onChange={(e) => setVerifyInputs({ ...verifyInputs, [s.id]: { ...inputs, amount_2: e.target.value } })}
                      className="w-24 px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
                    />
                    <button
                      onClick={() => handleVerify(s.id)}
                      disabled={verifying === s.id}
                      className="px-3 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50"
                    >
                      {verifying === s.id ? 'Verifying...' : 'Verify'}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}