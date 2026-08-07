import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/', label: 'Dashboard', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="3" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="14" y="12" width="7" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/><rect x="3" y="16" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8"/></svg>
  )},
  { path: '/approvals', label: 'Approvals', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/></svg>
  )},
  { path: '/clients', label: 'Clients', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.8"/><path d="M2.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><path d="M16 8.5a3 3 0 100-6M18 14c2.3.3 4 2.1 4 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/staff', label: 'Staff', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8"/><path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/audit-log', label: 'Audit Log', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" strokeWidth="1.8"/><path d="M14 2v6h6M8 13h8M8 17h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
  )},
  { path: '/reports', label: 'Reports', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><path d="M3 3v18h18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><rect x="7" y="12" width="3" height="6" rx="0.5" fill="currentColor"/><rect x="12" y="8" width="3" height="10" rx="0.5" fill="currentColor"/><rect x="17" y="5" width="3" height="13" rx="0.5" fill="currentColor"/></svg>
  )},
  { path: '/assistant', label: 'Assistant', icon: (p) => (
    <svg {...p} viewBox="0 0 24 24" fill="none"><path d="M12 3a7 7 0 00-7 7c0 2.1.9 3.98 2.34 5.29L7 21l4.2-1.6c.26.03.53.05.8.05a7 7 0 000-14z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="12" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
  )},
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen flex bg-paper-50">
      <aside className="w-64 bg-steel-900 text-white flex flex-col shrink-0">
        <div className="px-6 py-6 flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-crimson-600 flex items-center justify-center font-display font-bold text-sm">B</div>
          <div>
            <h1 className="font-display text-base font-semibold leading-none">Banking System</h1>
            <p className="text-slate-300 text-xs mt-1">Employee Portal</p>
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
                  active ? 'bg-crimson-600 text-white' : 'text-slate-300 hover:text-white hover:bg-steel-800'
                }`}
              >
                <Icon className="w-[18px] h-[18px] shrink-0" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="px-6 py-4 border-t border-steel-800">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-sm shrink-0">
              {user?.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide bg-steel-800 text-slate-300 px-1.5 py-0.5 rounded">
                {user?.role}
              </span>
            </div>
          </div>
          <button onClick={logout} className="text-xs text-slate-300 hover:text-white">
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto flex flex-col">
        <div className="flex-1">{children}</div>
        <footer className="mt-12 pt-6 border-t border-slate-300/40 flex justify-between items-center text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <rect x="5" y="11" width="14" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.8"/>
              <path d="M8 11V7a4 4 0 118 0v4" stroke="currentColor" strokeWidth="1.8"/>
            </svg>
            Internal system · Access is logged and monitored
          </div>
          <div className="flex gap-4">
            <span className="hover:text-steel-900 cursor-pointer transition">Compliance Guide</span>
            <span className="hover:text-steel-900 cursor-pointer transition">IT Support</span>
          </div>
        </footer>
      </main>
    </div>
  )
}