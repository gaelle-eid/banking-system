import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { formatMoney, formatDate } from '../lib/format'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/reports/summary'),
      api.get('/approvals?status=pending'),
    ]).then(([summaryRes, approvalsRes]) => {
      setSummary(summaryRes.data)
      setPending(approvalsRes.data.slice(0, 5))
      setLoading(false)
    })
  }, [])

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Overview</h1>
        <p className="text-slate-500 text-sm mt-1">Bank-wide status at a glance.</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-slate-300/20 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Pending approvals"
            value={summary.pending_approvals}
            accent
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 8v4l3 3" stroke="white" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="12" r="9" stroke="white" strokeWidth="2"/></svg>}
          />
          <StatCard
            label="Total client deposits"
            value={formatMoney(summary.total_balance)}
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>}
          />
          <StatCard
            label="Total clients"
            value={summary.total_clients}
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.5" stroke="currentColor" strokeWidth="2"/><path d="M2.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>}
          />
          <StatCard
            label="Transactions today"
            value={summary.transactions_today}
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M7 7h13M7 7l4-4M7 7l4 4M17 17H4M17 17l-4 4M17 17l-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
        </div>
      )}

      <div className="flex justify-between items-center mb-4">
        <h2 className="font-display text-lg font-semibold text-steel-900">Needs your review</h2>
        <Link to="/approvals" className="text-sm text-crimson-600 font-medium hover:underline">View all →</Link>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border border-slate-300/40 divide-y divide-slate-300/30">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-300/10 animate-pulse" />
          ))}
        </div>
      ) : pending.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center border border-slate-300/40">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <p className="text-slate-500">All caught up — no pending approvals.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-300/40 divide-y divide-slate-300/30">
          {pending.map((a) => (
            <div key={a.id} className="flex justify-between items-center px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-crimson-100 text-crimson-600 flex items-center justify-center shrink-0">
                  {a.entity_type === 'loan' ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="2.5" stroke="currentColor" strokeWidth="1.8"/><path d="M2 10h20" stroke="currentColor" strokeWidth="1.8"/></svg>
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium capitalize text-steel-900">{a.entity_type} request</p>
                  <p className="text-xs text-slate-500">{formatDate(a.created_at)}</p>
                </div>
              </div>
              <StatusBadge status={a.status} />
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}