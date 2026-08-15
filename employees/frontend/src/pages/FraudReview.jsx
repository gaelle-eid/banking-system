import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatDateTime } from '../lib/format'

const severityStyles = {
  low: 'bg-slate-300/30 text-slate-500',
  medium: 'bg-amber-100 text-amber-500',
  high: 'bg-crimson-100 text-crimson-600',
}

export default function FraudReview() {
  const [flags, setFlags] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [expandedId, setExpandedId] = useState(null)
  const [notes, setNotes] = useState('')
  const [processingId, setProcessingId] = useState(null)
  const { showToast } = useToast()

  async function loadFlags() {
    setLoading(true)
    const url = statusFilter ? `/fraud?status=${statusFilter}` : '/fraud'
    const res = await api.get(url)
    setFlags(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadFlags()
  }, [statusFilter])

  async function handleDecision(id, action) {
    setProcessingId(id)
    try {
      await api.post(`/fraud/${id}/${action}`, { notes: notes || null })
      showToast(action === 'clear' ? 'Marked as legitimate' : 'Confirmed fraud, account frozen')
      setExpandedId(null)
      setNotes('')
      await loadFlags()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not process decision', 'error')
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Fraud Review</h1>
        <p className="text-slate-500 text-sm mt-1">Transactions automatically flagged for unusual activity.</p>
      </div>

      <div className="flex gap-2 mb-6">
        {[{ label: 'Pending', value: 'pending' }, { label: 'Cleared', value: 'cleared' }, { label: 'Confirmed Fraud', value: 'confirmed_fraud' }, { label: 'All', value: '' }].map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              statusFilter === f.value ? 'bg-steel-900 text-white' : 'bg-white border border-slate-300/40 text-slate-500 hover:border-steel-900'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => <div key={i} className="h-20 bg-slate-300/10 rounded-xl animate-pulse" />)}
        </div>
      ) : flags.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center border border-slate-300/40">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <p className="text-slate-500">No {statusFilter || ''} flags right now.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {flags.map((flag) => (
            <div key={flag.id} className="bg-white rounded-xl border border-slate-300/40 overflow-hidden">
              <div
                className="flex justify-between items-center px-4 py-4 cursor-pointer"
                onClick={() => setExpandedId(expandedId === flag.id ? null : flag.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-crimson-100 text-crimson-600 flex items-center justify-center shrink-0">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" strokeWidth="1.8"/></svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-steel-900">{flag.reason.split('.')[0]}.</p>
                    <p className="text-xs text-slate-500">
                      {flag.client_name && `${flag.client_name} · `}Flagged {formatDateTime(flag.created_at)}
                    </p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${severityStyles[flag.severity]}`}>
                  {flag.severity}
                </span>
              </div>

              {expandedId === flag.id && (
                <div className="px-4 pb-4 border-t border-slate-300/30 pt-4">
                  <p className="text-sm text-steel-900 mb-3">{flag.reason}</p>
                  <div className="bg-slate-300/10 rounded-lg p-3 mb-4 space-y-1">
                    <p className="text-sm text-steel-900">
                      <span className="text-slate-500">Client:</span>{' '}
                      <span className="font-medium">{flag.client_name || 'Unknown client'}</span>
                      {flag.client_email && <span className="text-slate-500"> ({flag.client_email})</span>}
                    </p>
                    {flag.account_label && (
                      <p className="text-sm text-steel-900">
                        <span className="text-slate-500">Account:</span> {flag.account_label}
                      </p>
                    )}
                    {flag.transaction_details && (
                      <p className="text-sm text-steel-900 capitalize">
                        <span className="text-slate-500">Transaction:</span>{' '}
                        <span className="font-mono font-medium">
                          {flag.transaction_details.amount} {flag.transaction_details.currency}
                        </span>
                        {' '}({flag.transaction_details.type.replace('_', ' ')})
                        {flag.transaction_details.source && ` — ${flag.transaction_details.source}`}
                        {' · '}{formatDateTime(flag.transaction_details.created_at)}
                      </p>
                    )}
                    {flag.notes && (
                      <p className="text-sm text-steel-900">
                        <span className="text-slate-500">Notes:</span> {flag.notes}
                      </p>
                    )}
                  </div>

                  {flag.related_pending_flags && flag.related_pending_flags.length > 0 && (
                    <div className="bg-crimson-100 rounded-lg p-3 mb-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-crimson-600 mb-2">
                        {flag.related_pending_flags.length} other pending flag{flag.related_pending_flags.length !== 1 ? 's' : ''} for this client
                      </p>
                      <div className="space-y-1.5">
                        {flag.related_pending_flags.map((rf) => (
                          <p key={rf.id} className="text-xs text-crimson-600">
                            <span className="uppercase font-medium">{rf.severity}</span> — {rf.reason.split('.')[0]}. ({formatDateTime(rf.created_at)})
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  {flag.recent_transactions && flag.recent_transactions.length > 0 && (
                    <div className="border border-slate-300/40 rounded-lg p-3 mb-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">
                        Recent activity on this account
                      </p>
                      <div className="space-y-1">
                        {flag.recent_transactions.map((rtx, i) => (
                          <p key={i} className="text-xs text-steel-900 capitalize">
                            <span className="font-mono">{rtx.amount}</span> — {rtx.type.replace('_', ' ')}
                            {rtx.source && ` (${rtx.source})`}
                            <span className="text-slate-500"> · {formatDateTime(rtx.created_at)}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  {flag.status === 'pending' && (
                    <>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Add a note (optional)..."
                        rows={2}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-crimson-600"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDecision(flag.id, 'clear')}
                          disabled={processingId === flag.id}
                          className="px-4 py-2 bg-steel-900 text-white rounded-lg text-sm font-medium hover:bg-steel-800 transition disabled:opacity-50"
                        >
                          {processingId === flag.id ? 'Processing...' : 'Mark legitimate'}
                        </button>
                        <button
                          onClick={() => handleDecision(flag.id, 'confirm-fraud')}
                          disabled={processingId === flag.id}
                          className="px-4 py-2 border border-crimson-600 text-crimson-600 rounded-lg text-sm font-medium hover:bg-crimson-100 transition disabled:opacity-50"
                        >
                          Confirm fraud & freeze account
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}