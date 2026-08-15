import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

const TIER_STYLES = {
  standard: {
    base: 'linear-gradient(135deg, #1F1917 0%, #16110F 60%, #16110F 100%)',
    accent: 'linear-gradient(120deg, transparent 40%, rgba(120,113,108,0.35) 75%, rgba(120,113,108,0.55) 100%)',
  },
  cashback: {
    base: 'linear-gradient(135deg, #14251F 0%, #0E1A16 60%, #0E1A16 100%)',
    accent: 'linear-gradient(120deg, transparent 40%, rgba(16,145,90,0.35) 75%, rgba(16,145,90,0.55) 100%)',
  },
  travel: {
    base: 'linear-gradient(135deg, #131C2E 0%, #0D1420 60%, #0D1420 100%)',
    accent: 'linear-gradient(120deg, transparent 40%, rgba(37,99,235,0.35) 75%, rgba(37,99,235,0.55) 100%)',
  },
  premium: {
    base: 'linear-gradient(135deg, #23200F 0%, #17140A 60%, #17140A 100%)',
    accent: 'linear-gradient(120deg, transparent 40%, rgba(202,163,74,0.4) 75%, rgba(202,163,74,0.6) 100%)',
  },
}

export default function Cards() {
  const [cards, setCards] = useState([])
  const [accounts, setAccounts] = useState([])
  const [tierInfo, setTierInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [accountId, setAccountId] = useState('')
  const [cardType, setCardType] = useState('debit')
  const [cardTier, setCardTier] = useState('standard')
  const [showCompare, setShowCompare] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [cancellingId, setCancellingId] = useState(null)
  const [activatingId, setActivatingId] = useState(null)
  const [freezingId, setFreezingId] = useState(null)
  const { showToast } = useToast()

  async function loadData() {
    const [cardsRes, accountsRes, tierRes] = await Promise.all([
      api.get('/cards/me'),
      api.get('/accounts/me'),
      api.get('/cards/tier-info'),
    ])
    setCards(cardsRes.data)
    setAccounts(accountsRes.data)
    setTierInfo(tierRes.data)
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
      await api.post('/cards', { account_id: accountId, type: cardType, tier: cardTier })
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

  async function handleActivate(cardId) {
    setActivatingId(cardId)
    try {
      await api.patch(`/cards/${cardId}/activate`)
      showToast('Card activated')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not activate card', 'error')
    } finally {
      setActivatingId(null)
    }
  }

  async function handleToggleFreeze(cardId, isFrozen) {
    setFreezingId(cardId)
    try {
      await api.patch(`/cards/${cardId}/${isFrozen ? 'unfreeze' : 'freeze'}`)
      showToast(isFrozen ? 'Card unfrozen' : 'Card frozen')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not update card', 'error')
    } finally {
      setFreezingId(null)
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
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Tier</label>
              <select
                value={cardTier} onChange={(e) => setCardTier(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              >
                <option value="standard">Standard</option>
                <option value="cashback">Cashback</option>
                <option value="travel">Travel</option>
                <option value="premium">Premium</option>
              </select>
              {tierInfo && (
                <p className="text-xs text-stone-500 mt-1">
                  {tierInfo[cardTier].perks} ATM limit: ${Number(tierInfo[cardTier].atm_daily_limit).toFixed(0)}/day.
                </p>
              )}
              {tierInfo && tierInfo[cardTier].non_cash_perks?.length > 0 && (
                <ul className="text-xs text-stone-500 mt-1 list-disc list-inside space-y-0.5">
                  {tierInfo[cardTier].non_cash_perks.map((perk) => (
                    <li key={perk}>{perk}</li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                onClick={() => setShowCompare(!showCompare)}
                className="text-xs text-ink-950 underline mt-1"
              >
                {showCompare ? 'Hide comparison' : 'Compare all tiers'}
              </button>
              {showCompare && tierInfo && (
                <div className="mt-2 overflow-x-auto border border-stone-300/40 rounded-lg">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="text-left text-stone-500 bg-stone-300/10">
                        <th className="py-1.5 px-2 font-medium"></th>
                        <th className="py-1.5 px-2 font-medium capitalize">Standard</th>
                        <th className="py-1.5 px-2 font-medium capitalize">Cashback</th>
                        <th className="py-1.5 px-2 font-medium capitalize">Travel</th>
                        <th className="py-1.5 px-2 font-medium capitalize">Premium</th>
                      </tr>
                    </thead>
                    <tbody className="text-ink-950">
                      <tr className="border-t border-stone-300/40">
                        <td className="py-1.5 px-2 text-stone-500">ATM limit/day</td>
                        {['standard', 'cashback', 'travel', 'premium'].map((t) => (
                          <td key={t} className="py-1.5 px-2 font-mono">${Number(tierInfo[t].atm_daily_limit).toFixed(0)}</td>
                        ))}
                      </tr>
                      <tr className="border-t border-stone-300/40">
                        <td className="py-1.5 px-2 text-stone-500">Annual fee</td>
                        {['standard', 'cashback', 'travel', 'premium'].map((t) => (
                          <td key={t} className="py-1.5 px-2 font-mono">${Number(tierInfo[t].annual_fee).toFixed(0)}</td>
                        ))}
                      </tr>
                      <tr className="border-t border-stone-300/40">
                        <td className="py-1.5 px-2 text-stone-500">Rewards</td>
                        {['standard', 'cashback', 'travel', 'premium'].map((t) => (
                          <td key={t} className="py-1.5 px-2">{tierInfo[t].rewards}</td>
                        ))}
                      </tr>
                      <tr className="border-t border-stone-300/40">
                        <td className="py-1.5 px-2 text-stone-500">Foreign fee</td>
                        {['standard', 'cashback', 'travel', 'premium'].map((t) => (
                          <td key={t} className="py-1.5 px-2">{tierInfo[t].foreign_fee}</td>
                        ))}
                      </tr>
                      <tr className="border-t border-stone-300/40">
                        <td className="py-1.5 px-2 text-stone-500 align-top">Non-cash perks</td>
                        {['standard', 'cashback', 'travel', 'premium'].map((t) => (
                          <td key={t} className="py-1.5 px-2 align-top">
                            {tierInfo[t].non_cash_perks?.length > 0 ? (
                              <ul className="list-disc list-inside space-y-0.5">
                                {tierInfo[t].non_cash_perks.map((perk) => (
                                  <li key={perk}>{perk}</li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-stone-400">—</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
              <Link to="/assistant" className="text-xs text-crimson-600 hover:underline mt-1 inline-block">
                Not sure? Ask the Assistant to recommend a tier for you →
              </Link>
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
          {cards.map((card) => {
            const style = TIER_STYLES[card.tier] || TIER_STYLES.standard
            return (
            <div
              key={card.id}
              className="relative rounded-2xl p-6 overflow-hidden text-white"
              style={{ background: style.base }}
            >
              <div
                className="absolute inset-0"
                style={{ background: style.accent }}
              />
              <div className="relative">
                <div className="flex justify-between items-start mb-8">
                  <span className="text-xs uppercase tracking-wide text-stone-300">{card.type} · {card.tier}</span>
                  <div className="flex items-center gap-1.5">
                    {card.frozen && (
                      <span className="text-[10px] uppercase tracking-wide bg-white/15 text-white px-2 py-0.5 rounded-full">
                        Frozen
                      </span>
                    )}
                    <StatusBadge status={card.status} />
                  </div>
                </div>
                <p className="font-mono text-lg tracking-[0.2em] mb-1">{card.masked_number}</p>
                {card.account_nickname && (
                  <p className="text-xs text-stone-300 mb-1">Linked to {card.account_nickname}</p>
                )}
                <p className="text-xs text-stone-300 mb-3">Expires {formatDate(card.expiry_date)}</p>
                {tierInfo && tierInfo[card.tier] && (
                  <p className={`text-[11px] text-stone-300 ${tierInfo[card.tier]?.non_cash_perks?.length > 0 ? 'mb-1' : 'mb-3'}`}>
                    {tierInfo[card.tier].perks}
                  </p>
                )}
                {tierInfo && tierInfo[card.tier]?.non_cash_perks?.length > 0 && (
                  <ul className="text-[11px] text-stone-300 mb-3 list-disc list-inside space-y-0.5">
                    {tierInfo[card.tier].non_cash_perks.map((perk) => (
                      <li key={perk}>{perk}</li>
                    ))}
                  </ul>
                )}
                {card.status === 'active' && !card.activated_at && (
                  <div className="mb-1">
                    <p className="text-[11px] text-stone-300 mb-1.5">Approved - not yet activated</p>
                    <button
                      onClick={() => handleActivate(card.id)}
                      disabled={activatingId === card.id}
                      className="text-xs bg-white text-ink-950 px-2.5 py-1 rounded-md font-medium hover:bg-stone-100 transition disabled:opacity-50"
                    >
                      {activatingId === card.id ? 'Activating...' : 'Activate this card'}
                    </button>
                  </div>
                )}
                {card.status === 'active' && card.activated_at && (
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggleFreeze(card.id, card.frozen)}
                      disabled={freezingId === card.id}
                      className="text-xs bg-white text-ink-950 px-2.5 py-1 rounded-md font-medium hover:bg-stone-100 transition disabled:opacity-50"
                    >
                      {freezingId === card.id ? '...' : card.frozen ? 'Unfreeze' : 'Freeze this card'}
                    </button>
                    <button
                      onClick={() => handleCancel(card.id)}
                      disabled={cancellingId === card.id}
                      className="text-xs text-stone-300 hover:text-white underline disabled:opacity-50"
                    >
                      {cancellingId === card.id ? 'Cancelling...' : 'Cancel'}
                    </button>
                  </div>
                )}
              </div>
            </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}