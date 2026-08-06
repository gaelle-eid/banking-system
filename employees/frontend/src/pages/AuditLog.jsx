import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { formatDateTime } from '../lib/format'

const actionStyles = {
  approve: 'bg-emerald-100 text-emerald-600',
  reject: 'bg-crimson-100 text-crimson-600',
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
        <p className="text-slate-500 text-sm mt-1">Every approval and rejection, in order.</p>
      </div>

      <div className="flex gap-2 mb-6">
        {['', 'loan', 'card'].map((v) => (
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
          {logs.map((log) => (
            <div key={log.id} className="flex justify-between items-center px-4 py-3">
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${actionStyles[log.action] || 'bg-slate-300/30 text-slate-500'}`}>
                  {log.action}
                </span>
                <div>
                  <p className="text-sm font-medium capitalize text-steel-900">{log.entity_type} · {log.entity_id.slice(0, 8)}</p>
                  {log.details?.notes && <p className="text-xs text-slate-500">"{log.details.notes}"</p>}
                </div>
              </div>
              <p className="text-xs text-slate-500 font-mono">{formatDateTime(log.created_at)}</p>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}