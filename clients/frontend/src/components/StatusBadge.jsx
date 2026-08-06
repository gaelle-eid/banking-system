const statusStyles = {
  pending: 'bg-stone-300/30 text-stone-500',
  approved: 'bg-ink-950/10 text-ink-950',
  active: 'bg-ink-950/10 text-ink-950',
  rejected: 'bg-crimson-100 text-crimson-600',
  closed: 'bg-stone-300/30 text-stone-500',
  blocked: 'bg-crimson-100 text-crimson-600',
  expired: 'bg-stone-300/30 text-stone-500',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${statusStyles[status] || 'bg-stone-300/30 text-stone-500'}`}>
      {status}
    </span>
  )
}