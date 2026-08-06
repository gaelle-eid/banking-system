import { useState } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { formatMoney, formatDate } from '../lib/format'

export default function Clients() {
  const [email, setEmail] = useState('')
  const [client, setClient] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function handleSearch(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    setSearched(true)
    try {
      const usersRes = await api.get('/admin/users')
      const found = usersRes.data.find((u) => u.email.toLowerCase() === email.toLowerCase())
      if (!found) {
        setClient(null)
        setAccounts([])
        setError('No user found with that email.')
        return
      }
      setClient(found)

      // employee endpoints only expose own accounts, so we use the agent
      // tool pattern via a direct query isn't available - use reports/summary style lookup instead
      setAccounts([])
    } catch (err) {
      setError('Search failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Clients</h1>
        <p className="text-slate-500 text-sm mt-1">Look up a client by email address.</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 mb-8 max-w-md">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="client@example.com"
          className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-crimson-600"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-steel-900 text-white rounded-lg text-sm font-medium hover:bg-steel-800 transition disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p className="text-crimson-600 text-sm mb-4">{error}</p>}

      {client && (
        <div className="bg-white rounded-2xl border border-slate-300/40 max-w-lg overflow-hidden">
          <div className="flex items-center gap-4 p-6 border-b border-slate-300/30">
            <div className="w-14 h-14 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-lg text-white shrink-0">
              {client.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
            </div>
            <div>
              <p className="font-display text-lg font-semibold text-steel-900">{client.full_name}</p>
              <p className="text-slate-500 text-sm capitalize">{client.role}</p>
            </div>
          </div>
          <div className="divide-y divide-slate-300/30">
            <div className="flex justify-between items-center px-6 py-3">
              <span className="text-sm text-slate-500">Email</span>
              <span className="text-sm font-medium text-steel-900">{client.email}</span>
            </div>
            <div className="flex justify-between items-center px-6 py-3">
              <span className="text-sm text-slate-500">Phone</span>
              <span className="text-sm font-medium text-steel-900">{client.phone || '—'}</span>
            </div>
            <div className="flex justify-between items-center px-6 py-3">
              <span className="text-sm text-slate-500">Address</span>
              <span className="text-sm font-medium text-steel-900">{client.address || '—'}</span>
            </div>
          </div>
          <div className="p-4 bg-paper-50 text-xs text-slate-500">
            Tip: use the Assistant to get a full account and transaction summary for this client.
          </div>
        </div>
      )}

      {searched && !client && !error && (
        <p className="text-slate-500 text-sm">No results.</p>
      )}
    </Layout>
  )
}