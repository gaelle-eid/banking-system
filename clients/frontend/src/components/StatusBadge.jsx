const statusStyles = {
  pending: 'bg-amber-500/15 text-amber-600',
  approved: 'bg-teal-500/15 text-teal-600',
  active: 'bg-teal-500/15 text-teal-600',
  rejected: 'bg-coral-500/15 text-coral-500',
  closed: 'bg-slate-400/15 text-slate-600',
  blocked: 'bg-coral-500/15 text-coral-500',
  expired: 'bg-slate-400/15 text-slate-600',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${statusStyles[status] || 'bg-slate-400/15 text-slate-600'}`}>
      {status}
    </span>
  )
}