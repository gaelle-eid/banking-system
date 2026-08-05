import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import AccountCard from '../components/AccountCard'

export default function Dashboard() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  async function loadAccounts() {
    const res = await api.get('/accounts/me')
    setAccounts(res.data)
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

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-900">Your accounts</h1>
          <p className="text-slate-600 text-sm mt-1">Manage balances, transfers, and requests.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleCreateAccount('checking')}
            disabled={creating}
            className="px-4 py-2 bg-teal-500 text-white rounded-lg text-sm font-medium hover:bg-teal-600 transition disabled:opacity-50"
          >
            + Checking account
          </button>
          <button
            onClick={() => handleCreateAccount('savings')}
            disabled={creating}
            className="px-4 py-2 border border-slate-400/40 text-ink-900 rounded-lg text-sm font-medium hover:bg-white transition disabled:opacity-50"
          >
            + Savings account
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-600">Loading accounts...</p>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-400/20">
          <p className="text-slate-600">You don't have any accounts yet.</p>
          <p className="text-sm text-slate-400 mt-1">Create one above to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => (
            <AccountCard key={account.id} account={account} />
          ))}
        </div>
      )}
    </Layout>
  )
}