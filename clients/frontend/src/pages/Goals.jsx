import { useState, useEffect } from 'react'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatMoney } from '../lib/format'

export default function Goals() {
  const [goals, setGoals] = useState([])
  const [progress, setProgress] = useState({})
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [targetAmount, setTargetAmount] = useState('')
  const [sourceAccountId, setSourceAccountId] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [planFormId, setPlanFormId] = useState(null)
  const [planMode, setPlanMode] = useState('fixed')
  const [planAmount, setPlanAmount] = useState('')
  const [savingPlan, setSavingPlan] = useState(false)
  const { showToast } = useToast()

  async function loadData() {
    setLoading(true)
    const [goalsRes, accountsRes] = await Promise.all([
      api.get('/goals/me'),
      api.get('/accounts/me'),
    ])
    setGoals(goalsRes.data)
    const activeAccounts = accountsRes.data.filter((a) => a.status === 'active')
    setAccounts(activeAccounts)
    setSourceAccountId((prev) => prev || activeAccounts[0]?.id || '')

    const progressResults = await Promise.all(
      goalsRes.data.map((g) => api.get(`/goals/${g.id}/progress`).then((r) => [g.id, r.data]))
    )
    setProgress(Object.fromEntries(progressResults))
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/goals', {
        name,
        target_amount: parseFloat(targetAmount),
        source_account_id: sourceAccountId,
      })
      setName('')
      setTargetAmount('')
      setShowForm(false)
      await loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create goal')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSavePlan(goalId) {
    setSavingPlan(true)
    try {
      const body = { contribution_mode: planMode }
      if (planMode === 'fixed') body.fixed_monthly_amount = parseFloat(planAmount)
      await api.patch(`/goals/${goalId}/contribution`, body)
      showToast('Savings plan updated')
      setPlanFormId(null)
      setPlanAmount('')
      await loadData()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not update plan', 'error')
    } finally {
      setSavingPlan(false)
    }
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950">Savings Goals</h1>
          <p className="text-stone-500 text-sm mt-1">Track your progress toward what matters to you.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition"
        >
          {showForm ? 'Cancel' : '+ Create goal'}
        </button>
      </div>

      {showForm && (
        accounts.length === 0 ? (
          <div className="bg-white rounded-xl p-6 border border-stone-300/40 mb-8 max-w-md">
            <p className="text-sm text-stone-500">You need an active account before creating a goal.</p>
          </div>
        ) : (
        <form onSubmit={handleCreate} className="bg-white rounded-xl p-6 border border-stone-300/40 mb-8 max-w-md">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Goal name</label>
              <input
                type="text" required maxLength={60}
                value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Vacation, Emergency Fund, New Laptop"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Target amount</label>
              <input
                type="number" step="0.01" min="1" required
                value={targetAmount} onChange={(e) => setTargetAmount(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-950 mb-1">Funded from</label>
              <select
                required value={sourceAccountId} onChange={(e) => setSourceAccountId(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              >
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.nickname || a.account_number} ({a.type}, {a.currency})</option>
                ))}
              </select>
            </div>
            {error && <p className="text-crimson-600 text-sm">{error}</p>}
            <button disabled={submitting} className="w-full bg-ink-950 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
              {submitting ? 'Creating...' : 'Create goal'}
            </button>
          </div>
        </form>
        )
      )}

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => <div key={i} className="h-32 bg-stone-300/10 rounded-2xl animate-pulse" />)}
        </div>
      ) : goals.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-stone-300/40">
          <p className="text-stone-500">No savings goals yet.</p>
          <p className="text-sm text-stone-500/70 mt-1">Create one above, or ask the Assistant to set one up for you.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {goals.map((goal) => {
            const p = progress[goal.id]
            const percent = p?.percent_complete ?? 0
            const currency = p?.currency || goal.currency || 'USD'
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

                <div className="flex justify-between text-sm mb-3">
                  <span className="text-stone-500">
                    {formatMoney(p?.current_amount ?? 0, currency)} saved
                  </span>
                  <span className="text-ink-950 font-medium">
                    of {formatMoney(goal.target_amount, currency)}
                  </span>
                </div>

                {goal.contribution_mode === 'fixed' && goal.fixed_monthly_amount && (
                  <p className="text-xs text-stone-500 pt-3 border-t border-stone-300/20 mb-2">
                    Auto-saving {formatMoney(goal.fixed_monthly_amount, currency)}/month
                  </p>
                )}

                {planFormId === goal.id ? (
                  <div className="pt-3 border-t border-stone-300/20 space-y-2">
                    <select
                      value={planMode} onChange={(e) => setPlanMode(e.target.value)}
                      className="w-full px-2 py-1.5 border border-stone-300 rounded-lg text-xs"
                    >
                      <option value="fixed">Auto-save a fixed amount monthly</option>
                      <option value="variable">Remind me monthly, I'll decide</option>
                    </select>
                    {planMode === 'fixed' && (
                      <input
                        type="number" step="0.01" min="0.01"
                        value={planAmount} onChange={(e) => setPlanAmount(e.target.value)}
                        placeholder="Monthly amount"
                        className="w-full px-2 py-1.5 border border-stone-300 rounded-lg text-xs font-mono"
                      />
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSavePlan(goal.id)}
                        disabled={savingPlan || (planMode === 'fixed' && !planAmount)}
                        className="px-3 py-1.5 bg-ink-950 text-white rounded-lg text-xs font-medium hover:bg-ink-900 transition disabled:opacity-50"
                      >
                        {savingPlan ? 'Saving...' : 'Save plan'}
                      </button>
                      <button
                        onClick={() => setPlanFormId(null)}
                        className="px-3 py-1.5 border border-stone-300 text-ink-950 rounded-lg text-xs font-medium hover:bg-white transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => { setPlanFormId(goal.id); setPlanMode(goal.contribution_mode || 'fixed'); setPlanAmount(goal.fixed_monthly_amount || '') }}
                    className="text-xs text-crimson-600 hover:underline pt-2"
                  >
                    {goal.contribution_mode ? 'Change savings plan' : 'Set up a savings plan'}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}