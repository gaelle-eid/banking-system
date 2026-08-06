export default function StatCard({ label, value, icon, accent = false }) {
  return (
    <div className={`rounded-xl p-5 border ${accent ? 'bg-steel-900 text-white border-steel-900' : 'bg-white border-slate-300/40'}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs uppercase tracking-wide ${accent ? 'text-slate-300' : 'text-slate-500'}`}>{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${accent ? 'bg-crimson-600' : 'bg-crimson-100 text-crimson-600'}`}>
          {icon}
        </div>
      </div>
      <p className={`font-mono text-2xl font-medium ${accent ? 'text-white' : 'text-steel-900'}`}>{value}</p>
    </div>
  )
}
