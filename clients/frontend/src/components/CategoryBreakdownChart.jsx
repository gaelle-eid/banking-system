import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { categoryLabel, categoryIcon } from '../lib/categories'
import { formatMoney } from '../lib/format'

const COLORS = ['#C41E3A', '#16110F', '#B8AEAB', '#7A6F6B', '#D9C9A0', '#8B5E3C', '#4A6670', '#9B7EDE']

export default function CategoryBreakdownChart({ data, currency = 'USD' }) {
  const categories = data?.categories || []

  if (categories.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-stone-300/40 p-6 text-center">
        <p className="text-stone-500 text-sm">No categorized spending in the last {data?.days || 30} days yet.</p>
      </div>
    )
  }

  const chartData = categories.map((c) => ({
    name: categoryLabel(c.category),
    icon: categoryIcon(c.category),
    value: parseFloat(c.amount),
    percent: c.percent,
    category: c.category,
  }))

  return (
    <div className="bg-white rounded-xl border border-stone-300/40 p-4">
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <ResponsiveContainer width="100%" height={200} className="sm:max-w-[200px]">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={80}
              paddingAngle={2}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatMoney(value, currency)}
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: '1px solid #B8AEAB',
                fontFamily: 'IBM Plex Mono, monospace',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex-1 w-full space-y-1.5">
          {chartData.map((c, i) => (
            <div key={c.category} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-ink-950 truncate">{c.icon} {c.name}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                <span className="font-mono text-xs text-stone-500">{c.percent}%</span>
                <span className="font-mono text-sm text-ink-950">{formatMoney(c.value, currency)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}