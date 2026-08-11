import { useState, useEffect } from 'react'
import api from '../lib/api'
import { useToast } from '../context/ToastContext'

export default function JointInvitations({ onResolved }) {
  const [invitations, setInvitations] = useState([])
  const [loading, setLoading] = useState(true)
  const [respondingId, setRespondingId] = useState(null)
  const { showToast } = useToast()

  async function loadInvitations() {
    try {
      const res = await api.get('/accounts/joint-invitations/pending')
      setInvitations(res.data)
    } catch {
      setInvitations([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInvitations()
  }, [])

  async function handleRespond(invitationId, action) {
    setRespondingId(invitationId)
    try {
      await api.post(`/accounts/joint-invitations/${invitationId}/${action}`)
      setInvitations((prev) => prev.filter((inv) => inv.invitation_id !== invitationId))
      showToast(action === 'accept' ? 'Joint account added' : 'Invitation declined')
      onResolved?.()
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not respond to invitation', 'error')
    } finally {
      setRespondingId(null)
    }
  }

  if (loading || invitations.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-crimson-600/30 p-4 mb-8">
      <h3 className="font-medium text-sm mb-3 text-ink-950">Joint account invitations</h3>
      <div className="space-y-3">
        {invitations.map((inv) => (
          <div key={inv.invitation_id} className="flex justify-between items-center">
            <p className="text-sm text-ink-950">
              <strong>{inv.invited_by_name}</strong> invited you to{' '}
              {inv.account_nickname || inv.account_type} ({inv.masked_account_number})
            </p>
            <div className="flex gap-2 shrink-0 ml-3">
              <button
                onClick={() => handleRespond(inv.invitation_id, 'accept')}
                disabled={respondingId === inv.invitation_id}
                className="px-3 py-1.5 bg-ink-950 text-white rounded-lg text-xs font-medium hover:bg-ink-900 transition disabled:opacity-50"
              >
                Accept
              </button>
              <button
                onClick={() => handleRespond(inv.invitation_id, 'decline')}
                disabled={respondingId === inv.invitation_id}
                className="px-3 py-1.5 border border-stone-300 text-ink-950 rounded-lg text-xs font-medium hover:bg-white transition disabled:opacity-50"
              >
                Decline
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}