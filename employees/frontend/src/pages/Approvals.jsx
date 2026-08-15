import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import { formatDate } from '../lib/format'

const LARGE_LOAN_THRESHOLD_LABEL = '$10,000'

const filters = [
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'All', value: '' },
]

export default function Approvals() {
  const [approvals, setApprovals] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [expandedId, setExpandedId] = useState(null)
  const [notes, setNotes] = useState('')
  const [interestRate, setInterestRate] = useState('')
  const [processingId, setProcessingId] = useState(null)
  const { showToast } = useToast()
  const { user } = useAuth()

  async function loadApprovals() {
    setLoading(true)
    const url = statusFilter ? `/approvals?status=${statusFilter}` : '/approvals'
    const res = await api.get(url)
    setApprovals(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadApprovals()
  }, [statusFilter])

  async function handleDecision(id, decision, entityType) {
    if (decision === 'approve' && entityType === 'loan' && !interestRate) {
      showToast('Set an interest rate before approving this loan', 'error')
      return
    }
    setProcessingId(id)
    try {
      const payload = { notes: notes || null }
      if (entityType === 'loan' && interestRate) {
        payload.interest_rate = parseFloat(interestRate)
      }
      await api.post(`/approvals/${id}/${decision}`, payload)
      showToast(`Request ${decision}d`)
      setExpandedId(null)
      setNotes('')
      setInterestRate('')
      await loadApprovals()
    } catch (err) {
      showToast(err.response?.data?.detail || `Could not ${decision}`, 'error')
    } finally {
      setProcessingId(null)
    }
  }

  const entityIcon = (type) => type === 'loan' ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="2.5" stroke="currentColor" strokeWidth="1.8"/><path d="M2 10h20" stroke="currentColor" strokeWidth="1.8"/></svg>
  )

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Approvals</h1>
        <p className="text-slate-500 text-sm mt-1">Review and act on client requests.</p>
      </div>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
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
          {[1, 2, 3].map((i) => <div key={i} className="h-20 bg-slate-300/10 rounded-xl animate-pulse" />)}
        </div>
      ) : approvals.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center border border-slate-300/40">
          <p className="text-slate-500">No {statusFilter || ''} requests.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {approvals.map((a) => (
            <div key={a.id} className="bg-white rounded-xl border border-slate-300/40 overflow-hidden">
              <div
                className="flex justify-between items-center px-4 py-4 cursor-pointer"
                onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-crimson-100 text-crimson-600 flex items-center justify-center shrink-0">
                    {entityIcon(a.entity_type)}
                  </div>
                  <div>
                    <p className="text-sm font-medium capitalize text-steel-900">
                      {a.entity_type} request{a.requested_by_name ? ` — ${a.requested_by_name}` : ''}
                    </p>
                    <p className="text-xs text-slate-500">Requested {formatDate(a.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={a.status} />
                  <svg
                    width="16" height="16" viewBox="0 0 24 24" fill="none"
                    className={`text-slate-500 transition-transform ${expandedId === a.id ? 'rotate-180' : ''}`}
                  >
                    <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>

              {expandedId === a.id && (
                <div className="px-4 pb-4 border-t border-slate-300/30 pt-4">
                  <div className="bg-slate-300/10 rounded-lg p-3 mb-4 space-y-1">
                    <p className="text-sm text-steel-900">
                      <span className="text-slate-500">Client:</span>{' '}
                      <span className="font-medium">{a.requested_by_name || 'Unknown client'}</span>
                      {a.requested_by_email && <span className="text-slate-500"> ({a.requested_by_email})</span>}
                    </p>
                    {a.entity_type === 'loan' && a.details && (
                      <>
                        <p className="text-sm text-steel-900">
                          <span className="text-slate-500">Amount:</span>{' '}
                          <span className="font-mono font-medium">{a.details.amount} {a.details.currency}</span>
                          {' · '}
                          <span className="text-slate-500">Term:</span>{' '}
                          <span className="font-medium">{a.details.term_months} months</span>
                        </p>
                        {a.details.purpose && (
                          <p className="text-sm text-steel-900">
                            <span className="text-slate-500">Purpose:</span> {a.details.purpose}
                          </p>
                        )}
                        {a.details.disbursement_account && (
                          <p className="text-sm text-steel-900">
                            <span className="text-slate-500">Disburse to:</span> {a.details.disbursement_account}
                          </p>
                        )}
                      </>
                    )}
                    {a.entity_type === 'card' && a.details && (
                      <p className="text-sm text-steel-900 capitalize">
                        <span className="text-slate-500">Request:</span>{' '}
                        <span className="font-medium">{a.details.tier} {a.details.type}</span>
                        {a.details.account && <> for <span className="font-medium">{a.details.account}</span></>}
                      </p>
                    )}
                    {a.notes && (
                      <p className="text-sm text-steel-900">
                        <span className="text-slate-500">Notes:</span> {a.notes}
                      </p>
                    )}
                  </div>

                  {a.client_context && (
                    <div className="border border-slate-300/40 rounded-lg p-3 mb-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">Client history</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-steel-900">
                        <p><span className="text-slate-500">Member since:</span> {a.client_context.member_since ? formatDate(a.client_context.member_since) : '—'}</p>
                        <p><span className="text-slate-500">Verified:</span> {a.client_context.is_verified ? 'Yes' : 'No'}</p>
                        <p><span className="text-slate-500">Accounts:</span> {a.client_context.account_count}</p>
                        <p><span className="text-slate-500">Active loans:</span> {a.client_context.active_loans_count} ({a.client_context.active_loans_remaining} owed)</p>
                        <p><span className="text-slate-500">Active cards:</span> {a.client_context.active_cards_count}</p>
                        <p className={a.client_context.pending_fraud_flags > 0 ? 'text-crimson-600 font-medium' : ''}>
                          <span className={a.client_context.pending_fraud_flags > 0 ? '' : 'text-slate-500'}>Fraud flags:</span>{' '}
                          {a.client_context.pending_fraud_flags}
                          {a.client_context.highest_fraud_severity && ` (${a.client_context.highest_fraud_severity})`}
                        </p>
                      </div>
                    </div>
                  )}

                  {a.entity_type === 'loan' && a.details?.credit_assessment && (
                    <div className="border border-slate-300/40 rounded-lg p-3 mb-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 mb-2">Credit assessment</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-steel-900">
                        <p><span className="text-slate-500">Avg monthly income:</span> {a.details.credit_assessment.avg_monthly_income}</p>
                        <p><span className="text-slate-500">Existing monthly debt:</span> {a.details.credit_assessment.existing_monthly_debt}</p>
                        <p>
                          <span className="text-slate-500">Debt-to-income:</span>{' '}
                          {a.details.credit_assessment.debt_to_income_pct !== null ? `${a.details.credit_assessment.debt_to_income_pct}%` : 'N/A'}
                        </p>
                        <p>
                          <span className="text-slate-500">Risk tier:</span>{' '}
                          <span className={`font-medium ${
                            a.details.credit_assessment.risk_tier === 'High' ? 'text-crimson-600' :
                            a.details.credit_assessment.risk_tier === 'Medium' ? 'text-amber-600' : ''
                          }`}>
                            {a.details.credit_assessment.risk_tier}
                          </span>
                        </p>
                      </div>
                    </div>
                  )}

                  {a.requires_admin && (
                    <div className="bg-crimson-100 text-crimson-600 text-xs font-medium rounded-lg px-3 py-2 mb-4">
                      This loan is {LARGE_LOAN_THRESHOLD_LABEL} or more and requires admin sign-off.
                    </div>
                  )}

                  {a.status === 'pending' && (
                    <>
                      {a.entity_type === 'loan' && (
                        <div className="mb-3">
                          <label className="block text-xs font-medium text-slate-500 mb-1">
                            Interest rate (%) - required to approve
                          </label>
                          <input
                            type="number" step="0.01" min="0.01"
                            value={interestRate}
                            onChange={(e) => setInterestRate(e.target.value)}
                            placeholder="e.g. 7.5"
                            className="w-32 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-crimson-600"
                          />
                        </div>
                      )}
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Add a note (optional)..."
                        rows={2}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-crimson-600"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDecision(a.id, 'approve', a.entity_type)}
                          disabled={processingId === a.id || (a.requires_admin && user?.role !== 'admin')}
                          className="px-4 py-2 bg-steel-900 text-white rounded-lg text-sm font-medium hover:bg-steel-800 transition disabled:opacity-50"
                        >
                          {processingId === a.id
                            ? 'Processing...'
                            : a.requires_admin && user?.role !== 'admin'
                              ? 'Admin required'
                              : 'Approve'}
                        </button>
                        <button
                          onClick={() => handleDecision(a.id, 'reject', a.entity_type)}
                          disabled={processingId === a.id}
                          className="px-4 py-2 border border-crimson-600 text-crimson-600 rounded-lg text-sm font-medium hover:bg-crimson-100 transition disabled:opacity-50"
                        >
                          Reject
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