import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const features = [
  {
    title: 'AI Assistant',
    desc: 'Check balances, get transfers proposed for you, and ask anything — with every money move requiring your confirmation.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 3a7 7 0 00-7 7c0 2.1.9 3.98 2.34 5.29L7 21l4.2-1.6c.26.03.53.05.8.05a7 7 0 000-14z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="12" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
    ),
  },
  {
    title: 'Bank-level security',
    desc: 'Email verification, encrypted sessions, and real-time transaction monitoring keep your money and data protected.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><rect x="5" y="11" width="14" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><path d="M8 11V7a4 4 0 118 0v4" stroke="currentColor" strokeWidth="1.8"/></svg>
    ),
  },
  {
    title: 'Instant transfers',
    desc: 'Move money between your own accounts or to anyone else at the bank in seconds, no waiting for business days.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M7 7h13M7 7l4-4M7 7l4 4M17 17H4M17 17l-4 4M17 17l-4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
    ),
  },
  {
    title: 'Smart limits & protection',
    desc: 'Built-in transaction and daily limits help prevent mistakes and catch unusual activity before it becomes a problem.',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/></svg>
    ),
  },
]

export default function Home() {
  const { user, loading } = useAuth()

  if (loading) return null

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-paper-50">
      {/* Nav */}
      <header className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm text-white">B</div>
          <span className="font-display text-base font-semibold text-ink-950">Banking System</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="px-4 py-2 text-sm font-medium text-ink-950 hover:text-crimson-600 transition">
            Sign in
          </Link>
          <Link to="/register" className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition">
            Open an account
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-8 pt-16 pb-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <h1 className="font-display text-4xl md:text-5xl font-semibold text-ink-950 leading-tight mb-5">
            Banking built for how you actually live.
          </h1>
          <p className="text-stone-600 text-lg mb-8 leading-relaxed">
            Open accounts in minutes, move money instantly, and let an AI assistant handle the busywork — every transfer still needs your say-so.
          </p>
          <div className="flex gap-3">
            <Link to="/register" className="px-6 py-3 bg-crimson-600 text-white rounded-lg font-medium hover:bg-crimson-700 transition">
              Open an account
            </Link>
            <Link to="/login" className="px-6 py-3 border border-stone-300 text-ink-950 rounded-lg font-medium hover:bg-white transition">
              Sign in
            </Link>
          </div>
        </div>

        {/* Hero visual: stacked card mockup */}
        <div className="relative h-72 md:h-80">
          <div
            className="absolute top-6 left-6 right-0 bottom-0 rounded-2xl p-6 text-white overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #2A2320 0%, #1F1917 60%, #16110F 100%)' }}
          >
            <div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(120deg, transparent 40%, rgba(196,30,58,0.3) 75%, rgba(196,30,58,0.5) 100%)' }}
            />
            <div className="relative">
              <span className="text-xs uppercase tracking-wide text-stone-300">Checking</span>
              <p className="font-mono text-3xl font-medium mt-8 mb-1">$12,480.50</p>
              <p className="font-mono text-sm text-stone-300 tracking-[0.2em]">•••• 4821</p>
            </div>
          </div>
          <div
            className="absolute top-0 left-0 right-6 bottom-6 rounded-2xl p-6 text-white overflow-hidden shadow-xl"
            style={{ background: 'linear-gradient(135deg, #1F1917 0%, #16110F 60%, #16110F 100%)' }}
          >
            <div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(120deg, transparent 40%, rgba(196,30,58,0.35) 75%, rgba(196,30,58,0.55) 100%)' }}
            />
            <div className="relative">
              <span className="text-xs uppercase tracking-wide text-stone-300">Savings</span>
              <p className="font-mono text-3xl font-medium mt-8 mb-1">$5,204.00</p>
              <p className="font-mono text-sm text-stone-300 tracking-[0.2em]">•••• 7009</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-8 pb-24">
        <h2 className="font-display text-2xl font-semibold text-ink-950 mb-10 text-center">
          Everything you need, nothing you don't
        </h2>
        <div className="grid sm:grid-cols-2 gap-6">
          {features.map((f) => (
            <div key={f.title} className="bg-white rounded-2xl p-6 border border-stone-300/40">
              <div className="w-11 h-11 rounded-lg bg-crimson-100 text-crimson-600 flex items-center justify-center mb-4">
                {f.icon}
              </div>
              <h3 className="font-display text-lg font-semibold text-ink-950 mb-2">{f.title}</h3>
              <p className="text-stone-600 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="bg-ink-950 text-white">
        <div className="max-w-6xl mx-auto px-8 py-16 text-center">
          <h2 className="font-display text-2xl md:text-3xl font-semibold mb-4">
            Ready to get started?
          </h2>
          <p className="text-stone-300 mb-8">Opening an account takes less than five minutes.</p>
          <Link to="/register" className="inline-block px-6 py-3 bg-crimson-600 text-white rounded-lg font-medium hover:bg-crimson-700 transition">
            Open an account
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-8 py-8 flex justify-between items-center text-xs text-stone-500">
        <div className="flex items-center gap-1.5">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <rect x="5" y="11" width="14" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M8 11V7a4 4 0 118 0v4" stroke="currentColor" strokeWidth="1.8"/>
          </svg>
          Bank-level encryption · Your data is protected
        </div>
        <div className="flex gap-4">
          <span className="hover:text-ink-950 cursor-pointer transition">Privacy Policy</span>
          <span className="hover:text-ink-950 cursor-pointer transition">Terms of Service</span>
          <span className="hover:text-ink-950 cursor-pointer transition">Support</span>
        </div>
      </footer>
    </div>
  )
}