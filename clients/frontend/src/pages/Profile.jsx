import { useAuth } from '../context/AuthContext'
import Layout from '../components/Layout'

export default function Profile() {
  const { user } = useAuth()

  const fields = [
    { label: 'Full name', value: user?.full_name },
    { label: 'Email', value: user?.email },
    { label: 'Phone', value: user?.phone },
    { label: 'Address', value: user?.address },
    { label: 'Role', value: user?.role },
  ]

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-950 mb-1">Profile</h1>
      <p className="text-stone-500 text-sm mb-8">Your account details.</p>

      <div className="bg-white rounded-2xl border border-stone-300/40 max-w-lg overflow-hidden">
        <div className="flex items-center gap-4 p-6 border-b border-stone-300/30">
          <div className="w-16 h-16 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-xl text-white shrink-0">
            {user?.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div>
            <p className="font-display text-lg font-semibold text-ink-950">{user?.full_name}</p>
            <p className="text-stone-500 text-sm capitalize">{user?.role} account</p>
          </div>
        </div>

        <div className="divide-y divide-stone-300/30">
          {fields.map((field) => (
            <div key={field.label} className="flex justify-between items-center px-6 py-4">
              <span className="text-sm text-stone-500">{field.label}</span>
              <span className="text-sm font-medium text-ink-950">{field.value || '—'}</span>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  )
}