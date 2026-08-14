import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatMoney, formatDate } from '../lib/format'

export default function Statements() {
  const [accounts, setAccounts] = useState([])
  const [selectedAccount, setSelectedAccount] = useState('')
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [downloadingId, setDownloadingId] = useState(null)
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
    setExpandedId(null)
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

  async function handleDownload(stmt) {
    setDownloadingId(stmt.id)
    try {
      const res = await api.get(`/statements/detail/${stmt.id}/pdf`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `statement_${formatDate(stmt.period_start).replace(/\s|,/g, '_')}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showToast('Could not download PDF', 'error')
    } finally {
      setDownloadingId(null)
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
            <div className="space-y-3">
              {statements.map((stmt) => {
                const currency = stmt.currency || selectedAccountObj?.currency || 'USD'
                const isExpanded = expandedId === stmt.id
                return (
                <div key={stmt.id} className="bg-white rounded-xl border border-stone-300/40 overflow-hidden">
                  <div
                    className="flex justify-between items-center px-4 py-4 cursor-pointer"
                    onClick={() => setExpandedId(isExpanded ? null : stmt.id)}
                  >
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
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownload(stmt) }}
                        disabled={downloadingId === stmt.id}
                        className="text-xs px-3 py-1.5 border border-stone-300 rounded-lg font-medium text-ink-950 hover:bg-paper-50 transition disabled:opacity-50"
                      >
                        {downloadingId === stmt.id ? 'Downloading...' : 'Download PDF'}
                      </button>
                      <svg
                        width="16" height="16" viewBox="0 0 24 24" fill="none"
                        className={`text-stone-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      >
                        <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-stone-300/30 pt-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
                        <div>
                          <p className="text-xs text-stone-500">Opening balance</p>
                          <p className="font-mono font-medium text-ink-950">{formatMoney(stmt.opening_balance ?? 0, currency)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-stone-500">Closing balance</p>
                          <p className="font-mono font-medium text-ink-950">{formatMoney(stmt.closing_balance ?? 0, currency)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-stone-500">Total deposits</p>
                          <p className="font-mono font-medium text-ink-950">{formatMoney(stmt.total_deposits ?? 0, currency)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-stone-500">Total withdrawals</p>
                          <p className="font-mono font-medium text-ink-950">{formatMoney(stmt.total_withdrawals ?? 0, currency)}</p>
                        </div>
                      </div>

                      {!stmt.transactions_snapshot || stmt.transactions_snapshot.length === 0 ? (
                        <p className="text-sm text-stone-500">No transactions in this period.</p>
                      ) : (
                        <div className="border border-stone-300/40 rounded-lg overflow-hidden">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="bg-paper-50 text-stone-500 text-left">
                                <th className="px-3 py-2 font-medium">Date</th>
                                <th className="px-3 py-2 font-medium">Description</th>
                                <th className="px-3 py-2 font-medium text-right">Amount</th>
                                <th className="px-3 py-2 font-medium text-right">Balance</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-stone-300/30">
                              {stmt.transactions_snapshot.map((line, i) => {
                                const isCredit = line.type === 'deposit' || line.type === 'transfer_credit'
                                return (
                                  <tr key={i}>
                                    <td className="px-3 py-2 text-stone-500 whitespace-nowrap">{line.date}</td>
                                    <td className="px-3 py-2 text-ink-950">{line.description}</td>
                                    <td className={`px-3 py-2 text-right font-mono ${isCredit ? 'text-ink-950' : 'text-crimson-600'}`}>
                                      {isCredit ? '+' : '-'}{formatMoney(line.amount, currency)}
                                    </td>
                                    <td className="px-3 py-2 text-right font-mono text-stone-500">{formatMoney(line.running_balance, currency)}</td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </Layout>
  )
}