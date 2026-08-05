import { Link } from 'react-router-dom'
import { formatMoney } from '../lib/format'

export default function AccountCard({ account }) {
  return (
    <Link
      to={`/accounts/${account.id}`}
      className="block bg-ink-900 text-white rounded-2xl p-6 hover:scale-[1.02] transition-transform"
    >
      <div className="flex justify-between items-start mb-8">
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {account.type}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-400">
          {account.status}
        </span>
      </div>

      <p className="font-mono text-2xl font-medium mb-1">
        {formatMoney(account.balance, account.currency)}
      </p>
      <p className="font-mono text-sm text-slate-400 tracking-widest">
        {account.account_number}
      </p>
    </Link>
  )
}