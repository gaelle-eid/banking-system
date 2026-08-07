import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

export default function PendingRegistrations() {
  const [registrations, setRegistrations] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [notes, setNotes] = useState('')
  const [processingId, setProcessingId] = useState(null)
  const { showToast } = useToast()

  async function loadRegistrations() {
    setLoading(true)
    const res = await api.get('/registrations/pending')
    setRegistrations(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadRegistrations()
  }, [])

  async function handleDecision(userId, decision) {
    setProcessingId(userId)
    try {
      await api.post(`/registrations/${userId}/${decision}`, { notes: notes || null })
      showToast(`Application ${decision}d`)
      setExpandedId(null)
      setNotes('')
      await loadRegistrations()
    } catch (err) {
      showToast(err.response?.data?.detail || `Could not ${decision}`, 'error')
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Pending Registrations</h1>
        <p className="text-slate-500 text-sm mt-1">New client applications waiting for review.</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => <div key={i} className="h-20 bg-slate-300/10 rounded-xl animate-pulse" />)}
        </div>
      ) : registrations.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center border border-slate-300/40">
          <p className="text-slate-500">No pending applications right now.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {registrations.map((r) => (
            <div key={r.id} className="bg-white rounded-xl border border-slate-300/40 overflow-hidden">
              <div
                className="flex justify-between items-center px-4 py-4 cursor-pointer"
                onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-sm text-white shrink-0">
                    {r.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-steel-900">{r.full_name}</p>
                    <p className="text-xs text-slate-500">{r.email} · Applied {formatDate(r.created_at)}</p>
                  </div>
                </div>
                <svg
                  width="16" height="16" viewBox="0 0 24 24" fill="none"
                  className={`text-slate-500 transition-transform ${expandedId === r.id ? 'rotate-180' : ''}`}
                >
                  <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>

              {expandedId === r.id && (
                <div className="px-4 pb-4 border-t border-slate-300/30 pt-4">
                  <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                    <div><span className="text-slate-500">Phone:</span> {r.phone || '—'}</div>
                    <div><span className="text-slate-500">National ID:</span> {r.national_id || '—'}</div>
                    <div className="col-span-2"><span className="text-slate-500">Address:</span> {r.address || '—'}</div>
                    <div className="col-span-2">
                      <span className="text-slate-500">ID Photo:</span>{' '}
                      {r.national_id_photo_path ? 'Uploaded ✓' : 'Not provided'}
                    </div>
                  </div>

                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add a note (optional)..."
                    rows={2}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-crimson-600"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDecision(r.id, 'approve')}
                      disabled={processingId === r.id}
                      className="px-4 py-2 bg-steel-900 text-white rounded-lg text-sm font-medium hover:bg-steel-800 transition disabled:opacity-50"
                    >
                      {processingId === r.id ? 'Processing...' : 'Approve'}
                    </button>
                    <button
                      onClick={() => handleDecision(r.id, 'reject')}
                      disabled={processingId === r.id}
                      className="px-4 py-2 border border-crimson-600 text-crimson-600 rounded-lg text-sm font-medium hover:bg-crimson-100 transition disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}