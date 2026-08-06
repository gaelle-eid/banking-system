import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function SpendingChart({ transactions }) {
  // Group by day, sum outgoing vs incoming
  const grouped = {}
  transactions.forEach((tx) => {
    const day = new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const isCredit = tx.type.includes('credit') || tx.type === 'deposit'
    if (!grouped[day]) grouped[day] = { day, in: 0, out: 0 }
    if (isCredit) grouped[day].in += parseFloat(tx.amount)
    else grouped[day].out += parseFloat(tx.amount)
  })

  const data = Object.values(grouped).slice(-7)

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-stone-300/40 p-6 text-center">
        <p className="text-stone-500 text-sm">Not enough activity yet to show a chart.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-stone-300/40 p-4">
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} barGap={4}>
          <XAxis
            dataKey="day"
            tick={{ fontSize: 11, fill: '#7A6F6B' }}
            axisLine={{ stroke: '#B8AEAB' }}
            tickLine={false}
          />
          <YAxis hide />
          <Tooltip
            cursor={{ fill: 'rgba(196,30,58,0.05)' }}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: '1px solid #B8AEAB',
              fontFamily: 'IBM Plex Mono, monospace',
            }}
          />
          <Bar dataKey="out" name="Money out" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill="#C41E3A" />)}
          </Bar>
          <Bar dataKey="in" name="Money in" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill="#16110F" />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}