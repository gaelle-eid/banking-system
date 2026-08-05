import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { formatMoney, formatDate } from '../lib/format'

export default function Loans() {
  const [loans, setLoans] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [amount, setAmount] = useState('')
  const [rate, setRate] = useState('')
  const [term, setTerm] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function loadLoans() {
    const res = await api.get('/loans/me')
    setLoans(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadLoans()
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/loans', {
        amount: parseFloat(amount),
        interest_rate: parseFloat(rate),
        term_months: parseInt(term),
      })
      setAmount('')
      setRate('')
      setTerm('')
      setShowForm(false)
      await loadLoans()
    } catch (err) {
      setError(err.response?.data?.detail || 'Loan request failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-900">Loans</h1>
          <p className="text-slate-600 text-sm mt-1">Requests are reviewed by an employee before activation.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-teal-500 text-white rounded-lg text-sm font-medium hover:bg-teal-600 transition"
        >
          {showForm ? 'Cancel' : '+ Request loan'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 border border-slate-400/20 mb-8 max-w-md">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-ink-900 mb-1">Amount</label>
              <input
                type="number" step="0.01" min="1" required
                value={amount} onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-900 mb-1">Interest rate (%)</label>
              <input
                type="number" step="0.01" min="0.01" required
                value={rate} onChange={(e) => setRate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-900 mb-1">Term (months)</label>
              <input
                type="number" min="1" required
                value={term} onChange={(e) => setTerm(e.target.value)}
                className="w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm font-mono"
              />
            </div>
            {error && <p className="text-coral-500 text-sm">{error}</p>}
            <button disabled={submitting} className="w-full bg-ink-900 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-800 transition disabled:opacity-50">
              {submitting ? 'Submitting...' : 'Submit request'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-slate-600">Loading...</p>
      ) : loans.length === 0 ? (
        <p className="text-slate-600 text-sm">No loan requests yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-slate-400/20 divide-y divide-slate-400/10">
          {loans.map((loan) => (
            <div key={loan.id} className="flex justify-between items-center px-4 py-4">
              <div>
                <p className="font-mono font-medium">{formatMoney(loan.amount)}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {loan.interest_rate}% · {loan.term_months} months · {formatDate(loan.created_at)}
                </p>
              </div>
              <StatusBadge status={loan.status} />
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}