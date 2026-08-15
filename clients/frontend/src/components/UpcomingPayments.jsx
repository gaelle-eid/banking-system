import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import { formatMoney, formatDate } from '../lib/format'

function nextMonthlyContributionDate() {
  const now = new Date()
  // Goal auto-contributions run on the 1st of each month (see backend scheduler).
  // If today is before/on the 1st this month at midnight, that's already passed for the day,
  // so always point to the 1st of next month for a clear "upcoming" date.
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  return next
}

export default function UpcomingPayments() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [loansRes, goalsRes] = await Promise.all([
          api.get('/loans/me'),
          api.get('/goals/me'),
        ])

        const loanItems = (loansRes.data || [])
          .filter((l) => l.status === 'active' && l.next_payment_due && parseFloat(l.remaining_balance || 0) > 0)
          .map((l) => ({
            key: `loan-${l.id}`,
            label: 'Loan repayment',
            detail: l.purpose || 'Loan',
            amount: l.monthly_payment,
            date: new Date(l.next_payment_due),
            currency: 'USD',
            icon: '🏦',
            link: '/loans',
          }))

        const goalItems = (goalsRes.data || [])
          .filter((g) => g.active && g.contribution_mode === 'fixed' && g.fixed_monthly_amount)
          .map((g) => ({
            key: `goal-${g.id}`,
            label: `Auto-save · ${g.name}`,
            detail: 'Monthly contribution',
            amount: g.fixed_monthly_amount,
            date: nextMonthlyContributionDate(),
            currency: g.currency || 'USD',
            icon: '🐷',
            link: '/goals',
          }))

        const combined = [...loanItems, ...goalItems].sort((a, b) => a.date - b.date).slice(0, 5)
        setItems(combined)
      } catch {
        setItems([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-stone-300/40 divide-y divide-stone-300/30">
        {[1, 2].map((i) => (
          <div key={i} className="flex justify-between items-center px-4 py-3">
            <div className="h-3.5 w-32 bg-stone-300/20 rounded animate-pulse" />
            <div className="h-4 w-16 bg-stone-300/20 rounded animate-pulse" />
          </div>
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-stone-300/40 p-6 text-center">
        <p className="text-stone-500 text-sm">No upcoming payments - no active loans or auto-save goals.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-stone-300/40 divide-y divide-stone-300/30">
      {items.map((item) => (
        <Link
          key={item.key}
          to={item.link}
          className="flex justify-between items-center px-4 py-3 hover:bg-stone-300/5 transition"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 bg-ink-950/5 text-base">
              {item.icon}
            </div>
            <div>
              <p className="text-sm font-medium text-ink-950">{item.label}</p>
              <p className="text-xs text-stone-500">{item.detail} · Due {formatDate(item.date)}</p>
            </div>
          </div>
          <p className="font-mono text-sm font-medium text-ink-950">
            {formatMoney(item.amount, item.currency)}
          </p>
        </Link>
      ))}
    </div>
  )
}