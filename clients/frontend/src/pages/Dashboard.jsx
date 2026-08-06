import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import AccountCard from '../components/AccountCard'
import { formatMoney, formatDate } from '../lib/format'

export default function Dashboard() {
  const [accounts, setAccounts] = useState([])
  const [recentActivity, setRecentActivity] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  async function loadAccounts() {
    const res = await api.get('/accounts/me')
    setAccounts(res.data)

    const txResults = await Promise.all(
      res.data.map((acc) =>
        api.get(`/transactions/${acc.id}`).then((txRes) =>
          txRes.data.map((tx) => ({ ...tx, accountLabel: acc.nickname || acc.type }))
        )
      )
    )
    const merged = txResults.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 8)
    setRecentActivity(merged)
    setLoading(false)
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  async function handleCreateAccount(type) {
    setCreating(true)
    try {
      await api.post('/accounts', { type, currency: 'USD' })
      await loadAccounts()
    } finally {
      setCreating(false)
    }
  }

  const totalBalance = accounts.reduce((sum, a) => sum + parseFloat(a.balance), 0)
  const currency = accounts[0]?.currency || 'USD'

  return (
    <Layout>
      {/* Hero balance */}
      <div className="mb-10">
        <p className="text-stone-500 text-sm mb-1">Total balance</p>
        {loading ? (
          <div className="h-14 w-64 bg-stone-300/20 rounded-lg animate-pulse" />
        ) : (
          <p className="font-mono text-5xl md:text-6xl font-medium text-ink-950 tracking-tight">
            {formatMoney(totalBalance, currency)}
          </p>
        )}
        <p className="text-stone-500 text-sm mt-2">
          Across {accounts.length} account{accounts.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Account cards */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-display text-lg font-semibold text-ink-950">Your accounts</h2>
        <div className="flex gap-2">
          <button
            onClick={() => handleCreateAccount('checking')}
            disabled={creating}
            className="px-3 py-1.5 bg-crimson-600 text-white rounded-lg text-xs font-medium hover:bg-crimson-700 transition disabled:opacity-50"
          >
            + Checking
          </button>
          <button
            onClick={() => handleCreateAccount('savings')}
            disabled={creating}
            className="px-3 py-1.5 border border-stone-300 text-ink-950 rounded-lg text-xs font-medium hover:bg-white transition disabled:opacity-50"
          >
            + Savings
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-stone-500 mb-10">Loading accounts...</p>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-stone-300/40 mb-10">
          <p className="text-stone-500">You don't have any accounts yet.</p>
          <p className="text-sm text-stone-500/70 mt-1">Create one above to get started.</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-2 mb-10 -mx-1 px-1">
          {accounts.map((account) => (
            <div key={account.id} className="w-72 shrink-0">
              <AccountCard account={account} />
            </div>
          ))}
        </div>
      )}

      {/* Activity feed */}
      <h2 className="font-display text-lg font-semibold text-ink-950 mb-4">Recent activity</h2>
      {loading ? (
        <p className="text-stone-500">Loading...</p>
      ) : recentActivity.length === 0 ? (
        <p className="text-stone-500 text-sm">No recent activity.</p>
      ) : (
        <div className="bg-white rounded-xl border border-stone-300/40 divide-y divide-stone-300/30">
          {recentActivity.map((tx) => {
            const isCredit = tx.type.includes('credit') || tx.type === 'deposit'
            return (
              <div key={tx.id} className="flex justify-between items-center px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${
                    isCredit ? 'bg-ink-950/5 text-ink-950' : 'bg-crimson-600/10 text-crimson-600'
                  }`}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path
                        d={isCredit ? "M12 19V5M5 12l7-7 7 7" : "M12 5v14M5 12l7 7 7-7"}
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium capitalize text-ink-950">{tx.type.replace('_', ' ')}</p>
                    <p className="text-xs text-stone-500">{tx.accountLabel} · {formatDate(tx.created_at)}</p>
                  </div>
                </div>
                <p className={`font-mono text-sm font-medium ${isCredit ? 'text-ink-950' : 'text-crimson-600'}`}>
                  {isCredit ? '+' : '-'}{formatMoney(tx.amount, currency)}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}