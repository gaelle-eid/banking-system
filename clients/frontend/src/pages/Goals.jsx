import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { formatMoney } from '../lib/format'

export default function Goals() {
  const [goals, setGoals] = useState([])
  const [progress, setProgress] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const res = await api.get('/goals/me')
      setGoals(res.data)

      const progressResults = await Promise.all(
        res.data.map((g) => api.get(`/goals/${g.id}/progress`).then((r) => [g.id, r.data]))
      )
      setProgress(Object.fromEntries(progressResults))
      setLoading(false)
    }
    load()
  }, [])

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-ink-950">Savings Goals</h1>
        <p className="text-stone-500 text-sm mt-1">Track your progress toward what matters to you.</p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => <div key={i} className="h-32 bg-stone-300/10 rounded-2xl animate-pulse" />)}
        </div>
      ) : goals.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-stone-300/40">
          <p className="text-stone-500">No savings goals yet.</p>
          <p className="text-sm text-stone-500/70 mt-1">Ask the Assistant to set one up for you.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {goals.map((goal) => {
            const p = progress[goal.id]
            const percent = p?.percent_complete ?? 0
            return (
              <div key={goal.id} className="bg-white rounded-2xl p-6 border border-stone-300/40">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-display text-lg font-semibold text-ink-950">{goal.name}</h3>
                    <p className="text-xs text-stone-500 capitalize">
                      {goal.contribution_mode ? `${goal.contribution_mode} contributions` : 'No contribution plan set'}
                    </p>
                  </div>
                  <span className="text-2xl font-mono font-medium text-crimson-600">{percent}%</span>
                </div>

                <div className="w-full h-3 bg-stone-300/20 rounded-full overflow-hidden mb-3">
                  <div
                    className="h-full bg-crimson-600 rounded-full transition-all"
                    style={{ width: `${Math.min(percent, 100)}%` }}
                  />
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-stone-500">
                    {formatMoney(p?.current_amount ?? 0)} saved
                  </span>
                  <span className="text-ink-950 font-medium">
                    of {formatMoney(goal.target_amount)}
                  </span>
                </div>

                {goal.contribution_mode === 'fixed' && goal.fixed_monthly_amount && (
                  <p className="text-xs text-stone-500 mt-3 pt-3 border-t border-stone-300/20">
                    Auto-saving {formatMoney(goal.fixed_monthly_amount)}/month
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}