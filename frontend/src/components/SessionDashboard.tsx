import { useState, useEffect } from 'react'
import axios from 'axios'

interface Session {
  id: string
  name: string
  created_at: string
  message_count: number
  fold_count: number
}

export function SessionDashboard() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newSessionName, setNewSessionName] = useState('')

  useEffect(() => {
    fetchSessions()
  }, [])

  const fetchSessions = async () => {
    try {
      const res = await axios.get('/api/sessions')
      setSessions(res.data)
    } catch (err) {
      setError('Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  const createSession = async () => {
    if (!newSessionName.trim()) return
    try {
      const res = await axios.post('/api/sessions', { name: newSessionName })
      setSessions([res.data, ...sessions])
      setNewSessionName('')
    } catch {
      setError('Failed to create session')
    }
  }

  if (loading) return <div className="dashboard-loading">Loading sessions...</div>

  return (
    <section className="dashboard">
      <h2>Sessions</h2>
      {error && <div className="error">{error}</div>}
      <div className="create-session">
        <input
          type="text"
          value={newSessionName}
          onChange={e => setNewSessionName(e.target.value)}
          placeholder="New session name"
        />
        <button onClick={createSession}>Create</button>
      </div>
      <ul className="session-list">
        {sessions.map(session => (
          <li key={session.id} className="session-item">
            <span className="session-name">{session.name}</span>
            <span className="session-stats">
              {session.message_count} msgs, {session.fold_count} folds
            </span>
            <button onClick={() => window.location.href = `/session/${session.id}`}>
              Open
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}