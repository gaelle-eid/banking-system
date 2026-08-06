const statusStyles = {
  pending: 'bg-amber-100 text-amber-500',
  approved: 'bg-steel-900/10 text-steel-900',
  active: 'bg-steel-900/10 text-steel-900',
  rejected: 'bg-crimson-100 text-crimson-600',
  blocked: 'bg-crimson-100 text-crimson-600',
  active_status: 'bg-emerald-100 text-emerald-600',
  on_leave: 'bg-amber-100 text-amber-500',
  terminated: 'bg-crimson-100 text-crimson-600',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full capitalize font-medium ${statusStyles[status] || 'bg-slate-300/30 text-slate-500'}`}>
      {status?.replace('_', ' ')}
    </span>
  )
}