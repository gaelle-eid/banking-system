import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import StatCard from '../components/StatCard'
import { formatMoney } from '../lib/format'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts'

export default function Reports() {
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    api.get('/reports/summary').then((res) => setSummary(res.data))
  }, [])

  if (!summary) {
    return <Layout><p className="text-slate-500">Loading...</p></Layout>
  }

  const pieData = [
    { name: 'Clients', value: summary.total_clients },
    { name: 'Employees', value: summary.total_employees },
  ]
  const COLORS = ['#101820', '#C41E3A']

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-steel-900">Reports</h1>
        <p className="text-slate-500 text-sm mt-1">Live bank-wide performance snapshot.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total accounts" value={summary.total_accounts} icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="2"/><rect x="14" y="12" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="2"/></svg>} />
        <StatCard label="Total balance" value={formatMoney(summary.total_balance)} icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>} />
        <StatCard label="Active loans" value={summary.active_loans} icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>} />
        <StatCard label="Active cards" value={summary.active_cards} icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="2.5" stroke="currentColor" strokeWidth="2"/></svg>} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-300/40 p-6">
          <h2 className="font-display text-lg font-semibold text-steel-900 mb-4">User composition</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-slate-300/40 p-6">
          <h2 className="font-display text-lg font-semibold text-steel-900 mb-4">Today's activity</h2>
          <div className="flex items-center justify-center h-[220px]">
            <div className="text-center">
              <p className="font-mono text-5xl font-medium text-steel-900">{summary.transactions_today}</p>
              <p className="text-slate-500 text-sm mt-2">transactions processed today</p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}