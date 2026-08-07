import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

export default function Staff() {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [processingId, setProcessingId] = useState(null)
  const { showToast } = useToast()

  async function loadEmployees() {
    setLoading(true)
    const res = await api.get('/admin/employees')
    setEmployees(res.data)
    setLoading(false)
  }

  useEffect(() => {
    loadEmployees()
  }, [])

  async function handleStatusChange(userId, newStatus) {
    setProcessingId(userId)
    try {
      await api.patch(`/admin/employees/${userId}/status`, { status: newStatus })
      showToast(`Employee status updated to ${newStatus}`)
      await loadEmployees()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not update status', 'error')
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Staff</h1>
        <p className="text-slate-500 text-sm mt-1">Manage employee accounts and access.</p>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-slate-300/10 rounded-xl animate-pulse" />)}
        </div>
      ) : employees.length === 0 ? (
        <p className="text-slate-500 text-sm">No employees yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-slate-300/40 divide-y divide-slate-300/30">
          {employees.map((emp) => (
            <div key={emp.id} className="flex justify-between items-center px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-sm text-white shrink-0">
                  {emp.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
                </div>
                <div>
                  <p className="text-sm font-medium text-steel-900">{emp.full_name}</p>
                  <p className="text-xs text-slate-500">
                    {emp.profile?.job_title} · {emp.profile?.department} · {emp.email}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={emp.profile?.status} />
                {emp.profile?.status !== 'terminated' ? (
                  <button
                    onClick={() => handleStatusChange(emp.id, 'terminated')}
                    disabled={processingId === emp.id}
                    className="px-3 py-1.5 border border-crimson-600 text-crimson-600 rounded-lg text-xs font-medium hover:bg-crimson-100 transition disabled:opacity-50"
                  >
                    Terminate
                  </button>
                ) : (
                  <button
                    onClick={() => handleStatusChange(emp.id, 'active')}
                    disabled={processingId === emp.id}
                    className="px-3 py-1.5 border border-slate-300 text-steel-900 rounded-lg text-xs font-medium hover:bg-white transition disabled:opacity-50"
                  >
                    Reactivate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}