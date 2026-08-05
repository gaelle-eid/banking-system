import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { formatDate } from '../lib/format'

export default function Cards() {
  const [cards, setCards] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [accountId, setAccountId] = useState('')
  const [cardType, setCardType] = useState('debit')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function loadData() {
    const [cardsRes, accountsRes] = await Promise.all([
      api.get('/cards/me'),
      api.get('/accounts/me'),
    ])
    setCards(cardsRes.data)
    setAccounts(accountsRes.data)
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
      await api.post('/cards', { account_id: accountId, type: cardType })
      setAccountId('')
      setShowForm(false)
      await loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Card request failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-900">Cards</h1>
          <p className="text-slate-600 text-sm mt-1">Card requests are reviewed by an employee before activation.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-teal-500 text-white rounded-lg text-sm font-medium hover:bg-teal-600 transition"
        >
          {showForm ? 'Cancel' : '+ Request card'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 border border-slate-400/20 mb-8 max-w-md">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-ink-900 mb-1">Account</label>
              <select
                required value={accountId} onChange={(e) => setAccountId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm"
              >
                <option value="">Select account...</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.account_number} ({a.type})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-900 mb-1">Card type</label>
              <select
                value={cardType} onChange={(e) => setCardType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-400/40 rounded-lg text-sm"
              >
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
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
      ) : cards.length === 0 ? (
        <p className="text-slate-600 text-sm">No cards yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {cards.map((card) => (
            <div key={card.id} className="bg-ink-900 text-white rounded-2xl p-6">
              <div className="flex justify-between items-start mb-8">
                <span className="text-xs uppercase tracking-wide text-slate-400">{card.type}</span>
                <StatusBadge status={card.status} />
              </div>
              <p className="font-mono text-lg tracking-widest mb-1">{card.masked_number}</p>
              <p className="text-xs text-slate-400">Expires {formatDate(card.expiry_date)}</p>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}