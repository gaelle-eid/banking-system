import { useState, useRef, useEffect } from 'react'
import api from '../lib/api'
import ReactMarkdown from 'react-markdown'
import Layout from '../components/Layout'

export default function Assistant() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! I can check your accounts, transaction history, answer banking questions, or start a transfer for you. What do you need?" },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingActions, setPendingActions] = useState({})
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function extractActionId(text) {
    const labeledMatch = text.match(/action\s*id[:\s*`]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i)
    if (labeledMatch) return labeledMatch[1]
    // Fallback: the AI's proposal messages always contain exactly one UUID
    // (the action id) - if markdown formatting broke the labeled match above,
    // just grab any UUID-shaped string in the message.
    const anyUuid = text.match(/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i)
    return anyUuid ? anyUuid[1] : null
  }

  async function sendMessage(e) {
    e.preventDefault()
    if (!input.trim()) return

    setMessages((prev) => [...prev, { role: 'user', content: input }])
    setInput('')
    setLoading(true)

    try {
      const res = await api.post('/agent/client/chat', { message: input })
      const reply = res.data.reply
      const actionId = extractActionId(reply)

      setMessages((prev) => {
        const newIndex = prev.length
        if (actionId) {
          setPendingActions((pa) => ({ ...pa, [newIndex]: actionId }))
        }
        return [...prev, { role: 'assistant', content: reply }]
      })
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, something went wrong.' }])
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(index, actionId) {
    try {
      const res = await api.post(`/agent/client/actions/${actionId}/confirm`)
      let confirmMessage = 'Transfer confirmed and completed.'
      if (res.data.goal_account_nickname) {
        confirmMessage = `Savings goal "${res.data.goal_account_nickname}" created successfully.`
      } else if (res.data.goal_contribution) {
        confirmMessage = `Contribution of ${res.data.amount} completed successfully.`
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: confirmMessage }])
      setPendingActions((pa) => { const n = { ...pa }; delete n[index]; return n })
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: err.response?.data?.detail || 'Could not confirm.' }])
    }
  }

  async function handleReject(index, actionId) {
    try {
      await api.post(`/agent/client/actions/${actionId}/reject`)
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Cancelled.' }])
      setPendingActions((pa) => { const n = { ...pa }; delete n[index]; return n })
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: err.response?.data?.detail || 'Could not cancel.' }])
    }
  }

  return (
    <Layout>
      <h1 className="font-display text-2xl font-semibold text-ink-950 mb-6">Assistant</h1>

      <div className="bg-white rounded-2xl border border-stone-300/40 flex flex-col h-[calc(100vh-180px)] max-w-2xl">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                msg.role === 'user' ? 'bg-ink-950 text-white' : 'bg-paper-50 text-ink-950'
              }`}>
                <div className="prose prose-sm max-w-none [&_p]:m-0 [&_strong]:font-semibold">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
                {pendingActions[i] && (
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleConfirm(i, pendingActions[i])} className="px-3 py-1.5 bg-crimson-600 text-white rounded-lg text-xs font-medium hover:bg-crimson-700 transition">Confirm</button>
                    <button onClick={() => handleReject(i, pendingActions[i])} className="px-3 py-1.5 border border-stone-300 text-ink-950 rounded-lg text-xs font-medium hover:bg-white transition">Cancel</button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="flex justify-start"><div className="bg-paper-50 rounded-2xl px-4 py-2.5 text-sm text-stone-500">Thinking...</div></div>}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={sendMessage} className="border-t border-stone-300/40 p-3 flex gap-2">
          <input
            type="text" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your accounts, transfers, or savings goals..."
            className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-crimson-600"
          />
          <button type="submit" disabled={loading} className="px-4 py-2 bg-crimson-600 text-white rounded-lg text-sm font-medium hover:bg-crimson-700 transition disabled:opacity-50">Send</button>
        </form>
      </div>
    </Layout>
  )
}