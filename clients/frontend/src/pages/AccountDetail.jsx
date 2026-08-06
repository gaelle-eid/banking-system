import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import Layout from '../components/Layout'
import { formatMoney, formatDate } from '../lib/format'

export default function AccountDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [account, setAccount] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)

  const [depositAmount, setDepositAmount] = useState('')
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [transferAmount, setTransferAmount] = useState('')
  const [transferTo, setTransferTo] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  async function loadData() {
    const [accRes, txRes, allAccRes] = await Promise.all([
      api.get(`/accounts/${id}`),
      api.get(`/transactions/${id}`),
      api.get('/accounts/me'),
    ])
    setAccount(accRes.data)
    setTransactions(txRes.data)
    setAccounts(allAccRes.data.filter((a) => a.id !== id))
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [id])

  async function handleDeposit(e) {
    e.preventDefault()
    setActionError('')
    setActionLoading(true)
    try {
      await api.post('/transactions/deposit', { account_id: id, amount: parseFloat(depositAmount) })
      setDepositAmount('')
      await loadData()
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Deposit failed')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleWithdraw(e) {
    e.preventDefault()
    setActionError('')
    setActionLoading(true)
    try {
      await api.post('/transactions/withdraw', { account_id: id, amount: parseFloat(withdrawAmount) })
      setWithdrawAmount('')
      await loadData()
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Withdrawal failed')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleTransfer(e) {
    e.preventDefault()
    setActionError('')
    setActionLoading(true)
    try {
      await api.post('/transactions/transfer', {
        from_account_id: id,
        to_account_id: transferTo,
        amount: parseFloat(transferAmount),
      })
      setTransferAmount('')
      setTransferTo('')
      await loadData()
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Transfer failed')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) return <Layout><p className="text-stone-500">Loading...</p></Layout>
  if (!account) return <Layout><p className="text-crimson-600">Account not found.</p></Layout>

  return (
    <Layout>
      <button onClick={() => navigate('/')} className="text-sm text-stone-500 hover:text-ink-950 mb-4">
        ← Back to accounts
      </button>

      <div
        className="relative rounded-2xl p-6 mb-8 max-w-sm text-white overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1F1917 0%, #16110F 60%, #16110F 100%)' }}
      >
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(120deg, transparent 40%, rgba(196,30,58,0.35) 75%, rgba(196,30,58,0.55) 100%)' }}
        />
        <div className="relative">
          <span className="text-xs uppercase tracking-wide text-stone-300">{account.nickname || account.type}</span>
          <p className="font-mono text-3xl font-medium mt-2 mb-1 tracking-tight">
            {formatMoney(account.balance, account.currency)}
          </p>
          <p className="font-mono text-sm text-stone-300 tracking-[0.2em]">•••• {account.account_number.slice(-4)}</p>
        </div>
      </div>

      {actionError && <p className="text-crimson-600 text-sm mb-4">{actionError}</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <form onSubmit={handleDeposit} className="bg-white rounded-xl p-4 border border-stone-300/40">
          <h3 className="font-medium text-sm mb-3 text-ink-950">Deposit</h3>
          <input
            type="number" step="0.01" min="0.01" required
            value={depositAmount}
            onChange={(e) => setDepositAmount(e.target.value)}
            placeholder="Amount"
            className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2 font-mono"
          />
          <button disabled={actionLoading} className="w-full bg-ink-950 text-white py-2 rounded-lg text-sm font-medium hover:bg-ink-900 transition disabled:opacity-50">
            Deposit
          </button>
        </form>

        <form onSubmit={handleWithdraw} className="bg-white rounded-xl p-4 border border-stone-300/40">
          <h3 className="font-medium text-sm mb-3 text-ink-950">Withdraw</h3>
          <input
            type="number" step="0.01" min="0.01" required
            value={withdrawAmount}
            onChange={(e) => setWithdrawAmount(e.target.value)}
            placeholder="Amount"
            className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2 font-mono"
          />
          <button disabled={actionLoading} className="w-full bg-crimson-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50">
            Withdraw
          </button>
        </form>

        <form onSubmit={handleTransfer} className="bg-white rounded-xl p-4 border border-stone-300/40">
          <h3 className="font-medium text-sm mb-3 text-ink-950">Transfer</h3>
          <select
            required value={transferTo} onChange={(e) => setTransferTo(e.target.value)}
            className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2"
          >
            <option value="">To account...</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.nickname || a.account_number} ({a.type})</option>
            ))}
          </select>
          <input
            type="number" step="0.01" min="0.01" required
            value={transferAmount}
            onChange={(e) => setTransferAmount(e.target.value)}
            placeholder="Amount"
            className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm mb-2 font-mono"
          />
          <button disabled={actionLoading} className="w-full bg-crimson-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50">
            Transfer
          </button>
        </form>
      </div>

      <h2 className="font-display text-lg font-semibold mb-3 text-ink-950">Transaction history</h2>
      {transactions.length === 0 ? (
        <p className="text-stone-500 text-sm">No transactions yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-stone-300/40 divide-y divide-stone-300/30">
          {transactions.map((tx) => {
            const isCredit = tx.type.includes('credit') || tx.type === 'deposit'
            return (
              <div key={tx.id} className="flex justify-between items-center px-4 py-3">
                <div>
                  <p className="text-sm font-medium capitalize text-ink-950">{tx.type.replace('_', ' ')}</p>
                  <p className="text-xs text-stone-500">{formatDate(tx.created_at)}</p>
                </div>
                <p className={`font-mono text-sm font-medium ${isCredit ? 'text-ink-950' : 'text-crimson-600'}`}>
                  {isCredit ? '+' : '-'}{formatMoney(tx.amount, account.currency)}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </Layout>
  )
}