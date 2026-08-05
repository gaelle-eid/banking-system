import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/loans', label: 'Loans' },
  { path: '/cards', label: 'Cards' },
  { path: '/assistant', label: 'Assistant' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="min-h-screen flex bg-paper-50">
      <aside className="w-60 bg-ink-900 text-white flex flex-col shrink-0">
        <div className="px-6 py-6">
          <h1 className="font-display text-lg font-semibold">Banking System</h1>
          <p className="text-slate-400 text-xs mt-1">Client Portal</p>
        </div>

        <nav className="flex-1 px-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`block px-3 py-2 rounded-lg text-sm font-medium transition ${
                location.pathname === item.path
                  ? 'bg-teal-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-ink-800'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-ink-800">
          <p className="text-sm font-medium truncate">{user?.full_name}</p>
          <button onClick={logout} className="text-xs text-slate-400 hover:text-white mt-1">
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">{children}</main>
    </div>
  )
}