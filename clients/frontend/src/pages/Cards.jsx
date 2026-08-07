import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
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
  const [cancellingId, setCancellingId] = useState(null)
  const { showToast } = useToast()

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

  async function handleCancel(cardId) {
    setCancellingId(cardId)
    try {
      await api.patch(`/cards/${cardId}/cancel`)
      showToast('Card cancelled')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not cancel card', 'error')
    } finally {
      setCancellingId(null)
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950">Cards</h1>
          <p className="text-stone-500 text-sm mt-1">Card requests are reviewed by an employee before activation.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition"
        >
          {showForm ? 'Cancel' : '+ Request card'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 border border-stone-300/40 mb-8 max-w-md">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Account</label>
              <select
                required value={accountId} onChange={(e) => setAccountId(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              >
                <option value="">Select account...</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.nickname || a.account_number} ({a.type})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Card type</label>
              <select
                value={cardType} onChange={(e) => setCardType(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              >
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
            </div>
            {error && <p className="text-crimson-600 text-sm">{error}</p>}
            <button disabled={submitting} className="w-full bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
              {submitting ? 'Submitting...' : 'Submit request'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-stone-500">Loading...</p>
      ) : cards.length === 0 ? (
        <p className="text-stone-500 text-sm">No cards yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {cards.map((card) => (
            <div
              key={card.id}
              className="relative rounded-2xl p-6 overflow-hidden text-white"
              style={{ background: 'linear-gradient(135deg, #1F1917 0%, #16110F 60%, #16110F 100%)' }}
            >
              <div
                className="absolute inset-0"
                style={{ background: 'linear-gradient(120deg, transparent 40%, rgba(196,30,58,0.35) 75%, rgba(196,30,58,0.55) 100%)' }}
              />
              <div className="relative">
                <div className="flex justify-between items-start mb-8">
                  <span className="text-xs uppercase tracking-wide text-stone-300">{card.type}</span>
                  <StatusBadge status={card.status} />
                </div>
                <p className="font-mono text-lg tracking-[0.2em] mb-1">{card.masked_number}</p>
                <p className="text-xs text-stone-300 mb-3">Expires {formatDate(card.expiry_date)}</p>
                {card.status === 'active' && (
                  <button
                    onClick={() => handleCancel(card.id)}
                    disabled={cancellingId === card.id}
                    className="text-xs text-stone-300 hover:text-white underline disabled:opacity-50"
                  >
                    {cancellingId === card.id ? 'Cancelling...' : 'Cancel this card'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}