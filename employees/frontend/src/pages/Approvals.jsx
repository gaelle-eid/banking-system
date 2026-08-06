import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

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
  const [processingId, setProcessingId] = useState(null)
  const { showToast } = useToast()

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

  async function handleDecision(id, decision) {
    setProcessingId(id)
    try {
      await api.post(`/approvals/${id}/${decision}`, { notes: notes || null })
      showToast(`Request ${decision}d`)
      setExpandedId(null)
      setNotes('')
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
                    <p className="text-sm font-medium capitalize text-steel-900">{a.entity_type} request</p>
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
                  <div className="text-xs text-slate-500 space-y-1 mb-4 font-mono">
                    <p>Approval ID: {a.id}</p>
                    <p>Entity ID: {a.entity_id}</p>
                    <p>Requested by: {a.requested_by}</p>
                    {a.notes && <p>Notes: {a.notes}</p>}
                  </div>

                  {a.status === 'pending' && (
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
                          onClick={() => handleDecision(a.id, 'approve')}
                          disabled={processingId === a.id}
                          className="px-4 py-2 bg-steel-900 text-white rounded-lg text-sm font-medium hover:bg-steel-800 transition disabled:opacity-50"
                        >
                          {processingId === a.id ? 'Processing...' : 'Approve'}
                        </button>
                        <button
                          onClick={() => handleDecision(a.id, 'reject')}
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