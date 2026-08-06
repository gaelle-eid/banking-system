import { Link } from 'react-router-dom'
import { formatMoney } from '../lib/format'

export default function AccountCard({ account }) {
  return (
    <Link
      to={`/accounts/${account.id}`}
      className="relative block rounded-2xl p-6 overflow-hidden text-white hover:scale-[1.02] transition-transform"
      style={{
        background: 'linear-gradient(135deg, #1F1917 0%, #16110F 60%, #16110F 100%)',
      }}
    >
      <div
        className="absolute inset-0 opacity-90"
        style={{
          background: 'linear-gradient(120deg, transparent 40%, rgba(196,30,58,0.35) 75%, rgba(196,30,58,0.55) 100%)',
        }}
      />
      <div className="relative">
        <div className="flex justify-between items-start mb-10">
          <span className="text-xs uppercase tracking-wide text-stone-300">
            {account.nickname || account.type}
          </span>
          {/* chip glyph */}
          <svg width="28" height="20" viewBox="0 0 28 20" fill="none">
            <rect x="0.5" y="0.5" width="27" height="19" rx="3" stroke="#D9C9A0" strokeWidth="1"/>
            <line x1="9" y1="0.5" x2="9" y2="19.5" stroke="#D9C9A0" strokeWidth="0.75"/>
            <line x1="19" y1="0.5" x2="19" y2="19.5" stroke="#D9C9A0" strokeWidth="0.75"/>
            <line x1="0.5" y1="10" x2="27.5" y2="10" stroke="#D9C9A0" strokeWidth="0.75"/>
          </svg>
        </div>

        <p className="font-mono text-2xl font-medium mb-1 tracking-tight">
          {formatMoney(account.balance, account.currency)}
        </p>
        <p className="font-mono text-xs text-stone-300 tracking-[0.2em]">
          •••• {account.account_number.slice(-4)}
        </p>
      </div>
    </Link>
  )
}