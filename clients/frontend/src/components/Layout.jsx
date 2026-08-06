import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="3" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="12" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="3" y="16" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/></svg>
  )},
  { path: '/loans', label: 'Loans', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/cards', label: 'Cards', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="2.5" stroke="currentColor" strokeWidth="1.8"/><path d="M2 10h20" stroke="currentColor" strokeWidth="1.8"/></svg>
  )},
  { path: '/statements', label: 'Statements', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" strokeWidth="1.8"/><path d="M14 2v6h6M8 13h8M8 17h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/assistant', label: 'Assistant', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><path d="M12 3a7 7 0 00-7 7c0 2.1.9 3.98 2.34 5.29L7 21l4.2-1.6c.26.03.53.05.8.05a7 7 0 000-14z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="12" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
  )},
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen flex bg-paper-50">
      <aside className="w-60 bg-ink-950 text-white flex flex-col shrink-0">
        <div className="px-6 py-6 flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm">B</div>
          <div>
            <h1 className="font-display text-base font-semibold leading-none">Banking System</h1>
            <p className="text-stone-300 text-xs mt-1">Client Portal</p>
          </div>
        </div>

        <nav className="flex-1 px-3 space-y-1 mt-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  active ? 'bg-crimson-600 text-white' : 'text-stone-300 hover:text-white hover:bg-ink-900'
                }`}
              >
                <Icon className="w-[18px] h-[18px] shrink-0" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="px-6 py-4 border-t border-ink-900 flex items-center gap-3">
          <Link to="/profile" className="w-9 h-9 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-sm shrink-0 hover:opacity-80 transition">
            {user?.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
          </Link>
          <div className="min-w-0">
            <Link to="/profile" className="text-sm font-medium truncate block hover:text-crimson-600 transition">{user?.full_name}</Link>
            <button onClick={logout} className="text-xs text-stone-300 hover:text-white">
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto flex flex-col">
        <div className="flex-1">{children}</div>
        <footer className="mt-12 pt-6 border-t border-stone-300/30 flex justify-between items-center text-xs text-stone-500">
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
      </main>
    </div>
  )
}