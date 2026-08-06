import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

export default function Statements() {
  const [accounts, setAccounts] = useState([])
  const [selectedAccount, setSelectedAccount] = useState('')
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const { showToast } = useToast()

  async function loadAccounts() {
    const res = await api.get('/accounts/me')
    setAccounts(res.data)
    if (res.data.length > 0) {
      setSelectedAccount(res.data[0].id)
    }
    setLoading(false)
  }

  async function loadStatements(accountId) {
    if (!accountId) return
    const res = await api.get(`/statements/${accountId}`)
    setStatements(res.data)
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  useEffect(() => {
    loadStatements(selectedAccount)
  }, [selectedAccount])

  async function handleGenerate() {
    setGenerating(true)
    try {
      await api.post(`/statements/generate/${selectedAccount}`)
      await loadStatements(selectedAccount)
      showToast('Statement generated')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not generate statement', 'error')
    } finally {
      setGenerating(false)
    }
  }

  const selectedAccountObj = accounts.find((a) => a.id === selectedAccount)

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950">Statements</h1>
          <p className="text-stone-500 text-sm mt-1">View and generate account statements.</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !selectedAccount}
          className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50"
        >
          {generating ? 'Generating...' : '+ Generate statement'}
        </button>
      </div>

      {loading ? (
        <p className="text-stone-500">Loading...</p>
      ) : accounts.length === 0 ? (
        <p className="text-stone-500 text-sm">You need an account before generating statements.</p>
      ) : (
        <>
          <div className="mb-6 max-w-xs">
            <label className="block text-sm font-medium text-ink-950 mb-1">Account</label>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.nickname || a.account_number} ({a.type})</option>
              ))}
            </select>
          </div>

          {statements.length === 0 ? (
            <div className="bg-white rounded-2xl p-12 text-center border border-stone-300/40">
              <p className="text-stone-500">No statements for {selectedAccountObj?.nickname || 'this account'} yet.</p>
              <p className="text-sm text-stone-500/70 mt-1">Generate one above to get started.</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-stone-300/40 divide-y divide-stone-300/30">
              {statements.map((stmt) => (
                <div key={stmt.id} className="flex justify-between items-center px-4 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-ink-950/5 flex items-center justify-center text-ink-950 shrink-0">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" strokeWidth="1.8"/>
                        <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.8"/>
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink-950">
                        {formatDate(stmt.period_start)} – {formatDate(stmt.period_end)}
                      </p>
                      <p className="text-xs text-stone-500">Generated {formatDate(stmt.generated_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Layout>
  )
}