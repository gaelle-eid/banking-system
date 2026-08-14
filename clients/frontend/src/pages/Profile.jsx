import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../lib/api'
import Layout from '../components/Layout'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../lib/format'

export default function Profile() {
  const { user: contextUser } = useAuth()
  const [profile, setProfile] = useState(contextUser)
  const [loading, setLoading] = useState(true)

  const [editingContact, setEditingContact] = useState(false)
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [contactError, setContactError] = useState('')
  const [savingContact, setSavingContact] = useState(false)

  const [changingPassword, setChangingPassword] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

  const { showToast } = useToast()

  async function loadProfile() {
    const res = await api.get('/auth/me')
    setProfile(res.data)
    setPhone(res.data.phone || '')
    setAddress(res.data.address || '')
    setLoading(false)
  }

  useEffect(() => {
    loadProfile()
  }, [])

  async function handleSaveContact(e) {
    e.preventDefault()
    setContactError('')
    setSavingContact(true)
    try {
      await api.patch('/auth/me', { phone, address })
      await loadProfile()
      setEditingContact(false)
      showToast('Contact info updated')
    } catch (err) {
      setContactError(err.response?.data?.detail || 'Could not update contact info')
    } finally {
      setSavingContact(false)
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault()
    setPasswordError('')
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match')
      return
    }
    setSavingPassword(true)
    try {
      await api.post('/auth/me/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setChangingPassword(false)
      showToast('Password changed successfully')
    } catch (err) {
      const detail = err.response?.data?.detail
      setPasswordError(Array.isArray(detail) ? detail[0]?.msg : detail || 'Could not change password')
    } finally {
      setSavingPassword(false)
    }
  }

  if (loading || !profile) {
    return <Layout><p className="text-stone-500">Loading...</p></Layout>
  }

  const fields = [
    { label: 'Full name', value: profile.full_name },
    { label: 'Email', value: profile.email },
    { label: 'Phone', value: profile.phone, badge: profile.phone ? (profile.phone_verified ? { text: 'Verified', tone: 'good' } : { text: 'Unverified', tone: 'warn' }) : null },
    { label: 'Address', value: profile.address },
    { label: 'Date of birth', value: profile.date_of_birth ? formatDate(profile.date_of_birth) : null },
    { label: 'National ID', value: profile.national_id_masked },
    { label: 'Role', value: profile.role },
  ]

  return (
    <Layout>
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink-950 mb-1">Profile</h1>
          <p className="text-stone-500 text-sm">Your account details.</p>
        </div>
        <span className={`text-xs uppercase tracking-wide px-2.5 py-1 rounded-full font-medium ${
          profile.is_verified ? 'bg-ink-950/10 text-ink-950' : 'bg-crimson-600/10 text-crimson-600'
        }`}>
          {profile.is_verified ? 'Verified account' : profile.registration_status === 'pending_review' ? 'Pending review' : 'Not verified'}
        </span>
      </div>

      <div className="bg-white rounded-2xl border border-stone-300/40 max-w-lg overflow-hidden mb-6">
        <div className="flex items-center gap-4 p-6 border-b border-stone-300/30">
          <div className="w-16 h-16 rounded-full bg-crimson-600 flex items-center justify-center font-display font-semibold text-xl text-white shrink-0">
            {profile.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div>
            <p className="font-display text-lg font-semibold text-ink-950">{profile.full_name}</p>
            <p className="text-stone-500 text-sm capitalize">{profile.role} account</p>
          </div>
        </div>

        <div className="divide-y divide-stone-300/30">
          {fields.map((field) => (
            <div key={field.label} className="flex justify-between items-center px-6 py-4">
              <span className="text-sm text-stone-500">{field.label}</span>
              <span className="text-sm font-medium text-ink-950 flex items-center gap-2">
                {field.value || '—'}
                {field.badge && (
                  <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full ${
                    field.badge.tone === 'good' ? 'bg-ink-950/10 text-ink-950' : 'bg-crimson-600/10 text-crimson-600'
                  }`}>
                    {field.badge.text}
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-stone-300/40 max-w-lg p-6 mb-6">
        <div className="flex justify-between items-center mb-1">
          <h3 className="font-medium text-sm text-ink-950">Contact info</h3>
          {!editingContact && (
            <button onClick={() => setEditingContact(true)} className="text-xs text-crimson-600 hover:underline">
              Edit
            </button>
          )}
        </div>
        <p className="text-xs text-stone-500 mb-3">
          Phone and address can be updated here. Your legal name and national ID require support to change.
        </p>
        {editingContact && (
          <form onSubmit={handleSaveContact} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Phone</label>
              <input
                type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                placeholder="+96170123456"
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
              {phone !== (profile.phone || '') && (
                <p className="text-[11px] text-stone-500 mt-1">Changing your phone number will require re-verification.</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Address</label>
              <input
                type="text" value={address} onChange={(e) => setAddress(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            {contactError && <p className="text-crimson-600 text-xs">{contactError}</p>}
            <div className="flex gap-2">
              <button disabled={savingContact} className="px-4 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
                {savingContact ? 'Saving...' : 'Save changes'}
              </button>
              <button
                type="button"
                onClick={() => { setEditingContact(false); setPhone(profile.phone || ''); setAddress(profile.address || ''); setContactError('') }}
                className="px-4 py-2 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-paper-50 transition"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-stone-300/40 max-w-lg p-6">
        <div className="flex justify-between items-center mb-1">
          <h3 className="font-medium text-sm text-ink-950">Password</h3>
          {!changingPassword && (
            <button onClick={() => setChangingPassword(true)} className="text-xs text-crimson-600 hover:underline">
              Change password
            </button>
          )}
        </div>
        {!changingPassword && <p className="text-xs text-stone-500">••••••••••••</p>}
        {changingPassword && (
          <form onSubmit={handleChangePassword} className="space-y-3 mt-3">
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Current password</label>
              <input
                type="password" required value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">New password</label>
              <input
                type="password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
              <p className="text-[11px] text-stone-500 mt-1">8+ characters, with uppercase, lowercase, a number, and a special character.</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-500 mb-1">Confirm new password</label>
              <input
                type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm"
              />
            </div>
            {passwordError && <p className="text-crimson-600 text-xs">{passwordError}</p>}
            <div className="flex gap-2">
              <button disabled={savingPassword} className="px-4 py-2 bg-ink-950 text-white rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
                {savingPassword ? 'Saving...' : 'Update password'}
              </button>
              <button
                type="button"
                onClick={() => { setChangingPassword(false); setCurrentPassword(''); setNewPassword(''); setConfirmPassword(''); setPasswordError('') }}
                className="px-4 py-2 border border-stone-300 text-ink-950 rounded-lg text-sm font-medium hover:bg-paper-50 transition"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </Layout>
  )
}