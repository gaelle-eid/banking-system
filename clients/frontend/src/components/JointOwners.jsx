import { useState, useEffect } from 'react'
import api from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function JointOwners({ account, onChange }) {
  const { user } = useAuth()
  const { showToast } = useToast()
  const [owners, setOwners] = useState([])
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const isPrimaryOwner = account.owner_id === user?.id

  async function loadOwners() {
    setLoading(true)
    try {
      const res = await api.get(`/accounts/${account.id}/joint-owners`)
      setOwners(res.data)
    } catch {
      setOwners([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOwners()
  }, [account.id])

  async function handleInvite(e) {
    e.preventDefault()
    setError('')
    setAdding(true)
    try {
      await api.post(`/accounts/${account.id}/joint-owners`, { email })
      setEmail('')
      await loadOwners()
      onChange?.()
      showToast('Invitation sent')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not send invitation')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove(userId) {
    try {
      await api.delete(`/accounts/${account.id}/joint-owners/${userId}`)
      await loadOwners()
      onChange?.()
      showToast('Removed')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not remove', 'error')
    }
  }

  if (loading) return null

  // Nothing to show for a non-primary owner unless there are actually
  // joint owners to display, or for the primary owner to always show the
  // management UI.
  if (!isPrimaryOwner && owners.length === 0) return null

  return (
    <div className="bg-white rounded-xl p-4 border border-stone-300/40 mb-8 max-w-sm">
      <h3 className="font-medium text-sm mb-3 text-ink-950">Joint owners</h3>

      {owners.length === 0 ? (
        <p className="text-xs text-stone-500 mb-3">No joint owners on this account yet.</p>
      ) : (
        <div className="divide-y divide-stone-300/30 mb-3">
          {owners.map((o) => (
            <div key={o.user_id} className="flex justify-between items-center py-2">
              <div>
                <p className="text-sm text-ink-950">{o.full_name}</p>
                <p className="text-xs text-stone-500">{o.email}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {o.status === 'pending' && (
                  <span className="text-[10px] uppercase tracking-wide bg-stone-300/30 text-stone-500 px-2 py-0.5 rounded-full">
                    Pending
                  </span>
                )}
                {isPrimaryOwner && (
                  <button
                    onClick={() => handleRemove(o.user_id)}
                    className="text-xs text-crimson-600 hover:underline"
                  >
                    {o.status === 'pending' ? 'Cancel' : 'Remove'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {isPrimaryOwner && (
        <form onSubmit={handleInvite} className="flex gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Invite by email"
            className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm"
          />
          <button
            disabled={adding}
            className="px-3 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50"
          >
            {adding ? 'Sending...' : 'Invite'}
          </button>
        </form>
      )}
      {isPrimaryOwner && (
        <p className="text-xs text-stone-500 mt-2">
          They'll need to accept before they can access this account.
        </p>
      )}
      {error && <p className="text-crimson-600 text-xs mt-2">{error}</p>}
    </div>
  )
}