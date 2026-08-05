import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-paper-50 p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="font-display text-2xl font-semibold">Welcome, {user?.full_name}</h1>
        <button onClick={logout} className="text-sm text-slate-600 hover:text-ink-900">Sign out</button>
      </div>
      <p className="text-slate-600">Dashboard content coming in Part 2.</p>
    </div>
  )
}