import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { formatDateTime } from '../lib/format'

const actionStyles = {
  approve: 'bg-emerald-100 text-emerald-600',
  reject: 'bg-crimson-100 text-crimson-600',
  requested: 'bg-amber-100 text-amber-500',
  closed: 'bg-slate-300/30 text-slate-500',
  cancelled: 'bg-slate-300/30 text-slate-500',
}

function summarizeDetails(log) {
  const d = log.details
  if (!d) return null
  if (log.entity_type === 'loan' && d.amount) {
    return `$${d.amount} · ${d.term_months} months`
  }
  if (log.entity_type === 'card' && d.type) {
    return `${d.type} card`
  }
  if (log.entity_type === 'account' && d.nickname) {
    return d.nickname
  }
  if (d.notes) {
    return `"${d.notes}"`
  }
  return null
}

export default function AuditLog() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [entityFilter, setEntityFilter] = useState('')

  async function loadLogs() {
    setLoading(true)
    const url = entityFilter ? `/audit-logs?entity_type=${entityFilter}` : '/audit-logs'
    const res = await api.get(url)
    setLogs(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadLogs()
  }, [entityFilter])

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Audit Log</h1>
        <p className="text-slate-500 text-sm mt-1">Every client and staff action, in order.</p>
        <div className="mt-3 flex items-start gap-2 bg-amber-100 text-amber-500 rounded-lg px-3 py-2 text-xs max-w-xl">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="shrink-0 mt-0.5"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/><path d="M12 8v5M12 16h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
          <span>A record of every action taken by clients or staff — requests, approvals, rejections, closures, cancellations. Used for compliance and internal accountability. Clients don't have visibility into this.</span>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {['', 'loan', 'card', 'account'].map((v) => (
          <button
            key={v}
            onClick={() => setEntityFilter(v)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition ${
              entityFilter === v ? 'bg-steel-900 text-white' : 'bg-white border border-slate-300/40 text-slate-500 hover:border-steel-900'
            }`}
          >
            {v || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-14 bg-slate-300/10 rounded-lg animate-pulse" />)}
        </div>
      ) : logs.length === 0 ? (
        <p className="text-slate-500 text-sm">No audit entries yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-slate-300/40 divide-y divide-slate-300/30">
          {logs.map((log) => {
            const summary = summarizeDetails(log)
            return (
              <div key={log.id} className="flex justify-between items-center px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize shrink-0 ${actionStyles[log.action] || 'bg-slate-300/30 text-slate-500'}`}>
                    {log.action}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-steel-900">
                      <span className="capitalize">{log.entity_type}</span> · {log.actor_name || 'Unknown'}
                    </p>
                    {summary && <p className="text-xs text-slate-500">{summary}</p>}
                  </div>
                </div>
                <p className="text-xs text-slate-500 font-mono shrink-0">{formatDateTime(log.created_at)}</p>
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}