import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
import { formatMoney, formatDate } from '../lib/format'

export default function Loans() {
  const [loans, setLoans] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [amount, setAmount] = useState('')
  const [term, setTerm] = useState('')
  const [purpose, setPurpose] = useState('')
  const [disbursementAccountId, setDisbursementAccountId] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [payAmounts, setPayAmounts] = useState({})
  const [payingId, setPayingId] = useState(null)
  const { showToast } = useToast()

  async function loadData() {
    const [loansRes, accountsRes] = await Promise.all([
      api.get('/loans/me'),
      api.get('/accounts/me'),
    ])
    setLoans(loansRes.data)
    const activeAccounts = accountsRes.data.filter((a) => a.status === 'active')
    setAccounts(activeAccounts)
    setDisbursementAccountId((prev) => prev || activeAccounts[0]?.id || '')
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/loans', {
        amount: parseFloat(amount),
        term_months: parseInt(term),
        purpose: purpose.trim() || undefined,
        disbursement_account_id: disbursementAccountId,
      })
      setAmount('')
      setTerm('')
      setPurpose('')
      setShowForm(false)
      await loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Loan request failed')
    } finally {
      setSubmitting(false)
    }
  }

  async function handlePayment(loanId) {
    const amt = parseFloat(payAmounts[loanId])
    if (!amt || amt <= 0) return
    setPayingId(loanId)
    try {
      await api.post(`/loans/${loanId}/repay`, { amount: amt })
      setPayAmounts((prev) => ({ ...prev, [loanId]: '' }))
      showToast('Payment applied')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Payment failed', 'error')
    } finally {
      setPayingId(null)
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950">Loans</h1>
          <p className="text-stone-500 text-sm mt-1">
            Requests are reviewed by an employee, who sets your rate. Funds are deposited automatically once approved, with payments auto-debited monthly.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition"
        >
          {showForm ? 'Cancel' : '+ Request loan'}
        </button>
      </div>

      {showForm && (
        accounts.length === 0 ? (
          <div className="bg-white rounded-xl p-6 border border-stone-300/40 mb-8 max-w-md">
            <p className="text-sm text-stone-500">You need an active account to receive loan funds before requesting a loan.</p>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 border border-stone-300/40 mb-8 max-w-md">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Amount</label>
              <input
                type="number" step="0.01" min="1" required
                value={amount} onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Term (months)</label>
              <input
                type="number" min="1" required
                value={term} onChange={(e) => setTerm(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Purpose (optional)</label>
              <input
                type="text" maxLength={100}
                value={purpose} onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Home improvement, Car, Education"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Deposit funds into</label>
              <select
                required value={disbursementAccountId} onChange={(e) => setDisbursementAccountId(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              >
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.nickname || a.account_number} ({a.type}, {a.currency})</option>
                ))}
              </select>
            </div>
            <p className="text-xs text-stone-500">
              Your interest rate will be set by the bank as part of reviewing this request. Monthly payments will be auto-debited from this same account.
            </p>
            {error && <p className="text-crimson-600 text-sm">{error}</p>}
            <button disabled={submitting} className="w-full bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
              {submitting ? 'Submitting...' : 'Submit request'}
            </button>
          </div>
        </form>
        )
      )}

      {loading ? (
        <p className="text-stone-500">Loading...</p>
      ) : loans.length === 0 ? (
        <p className="text-stone-500 text-sm">No loan requests yet.</p>
      ) : (
        <div className="space-y-3">
          {loans.map((loan) => {
            const currency = accounts.find((a) => a.id === loan.disbursement_account_id)?.currency || 'USD'
            return (
            <div key={loan.id} className="bg-white rounded-xl border border-stone-300/40 p-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-mono font-medium text-ink-950">{formatMoney(loan.amount, currency)}</p>
                  <p className="text-xs text-stone-500 mt-0.5">
                    {loan.interest_rate != null ? `${loan.interest_rate}% · ` : 'Rate pending · '}
                    {loan.term_months} months
                    {loan.purpose ? ` · ${loan.purpose}` : ''} · {formatDate(loan.created_at)}
                  </p>
                  {loan.disbursed_at && (
                    <p className="text-xs text-ink-950 mt-0.5">Funds deposited {formatDate(loan.disbursed_at)}</p>
                  )}
                </div>
                <StatusBadge status={loan.status} />
              </div>

              {loan.status === 'active' && loan.remaining_balance != null && (
                <div className="mt-3 pt-3 border-t border-stone-300/30">
                  <div className="grid grid-cols-3 gap-3 text-xs mb-3">
                    <div>
                      <p className="text-stone-500">Remaining balance</p>
                      <p className="font-mono font-medium text-ink-950">{formatMoney(loan.remaining_balance, currency)}</p>
                    </div>
                    <div>
                      <p className="text-stone-500">Monthly payment</p>
                      <p className="font-mono font-medium text-ink-950">{formatMoney(loan.monthly_payment, currency)}</p>
                    </div>
                    <div>
                      <p className="text-stone-500">Next payment due</p>
                      <p className="font-medium text-ink-950">{loan.next_payment_due ? formatDate(loan.next_payment_due) : '—'}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="number" step="0.01" min="0.01"
                      value={payAmounts[loan.id] || ''}
                      onChange={(e) => setPayAmounts((prev) => ({ ...prev, [loan.id]: e.target.value }))}
                      placeholder="Extra payment amount"
                      className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
                    />
                    <button
                      onClick={() => handlePayment(loan.id)}
                      disabled={payingId === loan.id}
                      className="px-3 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50"
                    >
                      {payingId === loan.id ? 'Paying...' : 'Make a payment'}
                    </button>
                  </div>
                </div>
              )}

              {loan.status === 'closed' && (
                <p className="text-xs text-ink-950 mt-2 pt-2 border-t border-stone-300/30">Paid off in full.</p>
              )}
            </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}