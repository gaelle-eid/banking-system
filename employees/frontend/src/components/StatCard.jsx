export default function StatCard({ label, value, icon, accent = false, danger = false }) {
  const tone = danger ? 'danger' : accent ? 'dark' : 'default'
  const styles = {
    default: { card: 'bg-white border-slate-300/40', label: 'text-slate-500', iconWrap: 'bg-crimson-100 text-crimson-600', value: 'text-steel-900' },
    dark: { card: 'bg-steel-900 text-white border-steel-900', label: 'text-slate-300', iconWrap: 'bg-crimson-600', value: 'text-white' },
    danger: { card: 'bg-crimson-600 text-white border-crimson-600', label: 'text-white/80', iconWrap: 'bg-white/20', value: 'text-white' },
  }[tone]

  return (
    <div className={`rounded-xl p-5 border ${styles.card}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs uppercase tracking-wide ${styles.label}`}>{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${styles.iconWrap}`}>
          {icon}
        </div>
      </div>
      <p className={`font-mono text-2xl font-medium ${styles.value}`}>{value}</p>
    </div>
  )
}