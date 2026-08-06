import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/', label: 'Dashboard', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="3" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="12" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="3" y="16" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/></svg>
  )},
  { path: '/loans', label: 'Loans', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/cards', label: 'Cards', icon: (props) => (
    <svg {...props} viewBox="0 0 24 24" fill="none"><rect x="2" y="5" width="20" height="14" rx="2.5" stroke="currentColor" strokeWidth="1.8"/><path d="M2 10h20" stroke="currentColor" strokeWidth="1.8"/></svg>
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

        <div className="px-6 py-4 border-t border-ink-900">
          <p className="text-sm font-medium truncate">{user?.full_name}</p>
          <button onClick={logout} className="text-xs text-stone-300 hover:text-white mt-1">
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">{children}</main>
    </div>
  )
}