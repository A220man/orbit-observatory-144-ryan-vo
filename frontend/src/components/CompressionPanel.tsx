import { useState, useEffect } from 'react'
import axios from 'axios'

interface Message {
  ref: string
  role: string
  content: string
  token_count: number
}

interface Fold {
  id: string
  start_ref: string
  end_ref: string
  summary: string
  token_count: number
}

interface CompressibleSpan {
  start_ref: string
  end_ref: string
  token_count: number
}

export function CompressionPanel() {
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [folds, setFolds] = useState<Fold[]>([])
  const [spans, setSpans] = useState<CompressibleSpan[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadSession = async () => {
    if (!sessionId) return
    setLoading(true)
    setError('')
    try {
      const [msgRes, foldRes, statusRes] = await Promise.all([
        axios.get(`/api/sessions/${sessionId}/messages`),
        axios.get(`/api/sessions/${sessionId}/folds`),
        axios.post('/api/acp_status', { session_id: sessionId }),
      ])
      setMessages(msgRes.data)
      setFolds(foldRes.data)
      setSpans(statusRes.data.compressible_spans || [])
      setSuccess('Session loaded')
    } catch (err) {
      setError('Failed to load session')
    } finally {
      setLoading(false)
    }
  }

  const compress = async (startRef: string, endRef: string, dryRun = false) => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('/api/compress', {
        session_id: sessionId,
        start_ref: startRef,
        end_ref: endRef,
        dry_run: dryRun,
      })
      if (dryRun) {
        setSuccess(`Dry-run: would save ~${res.data.ranges[0]?.estimated_tokens_saved} tokens`)
      } else {
        await loadSession()
        setSuccess('Compressed successfully')
      }
    } catch (err) {
      setError('Compression failed')
    } finally {
      setLoading(false)
    }
  }

  const decompress = async (foldId: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('/api/decompress', { session_id: sessionId, ref: foldId })
      alert(res.data.content)
    } catch {
      setError('Decompression failed')
    } finally {
      setLoading(false)
    }
  }

  const search = async (query: string) => {
    if (!query.trim()) return
    try {
      const res = await axios.post('/api/search', { session_id: sessionId, query })
      alert(JSON.stringify(res.data.results, null, 2))
    } catch {
      setError('Search failed')
    }
  }

  return (
    <section className="compression-panel">
      <h2>Compression Panel</h2>
      <div className="session-selector">
        <input
          type="text"
          value={sessionId}
          onChange={e => setSessionId(e.target.value)}
          placeholder="Session ID"
        />
        <button onClick={loadSession} disabled={loading}>
          {loading ? 'Loading...' : 'Load Session'}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <div className="panel-grid">
        <div className="panel-section">
          <h3>Compressible Spans</h3>
          <ul>
            {spans.map((span, i) => (
              <li key={i}>
                {span.start_ref} - {span.end_ref} ({span.token_count} tokens)
                <button onClick={() => compress(span.start_ref, span.end_ref, true)}>Dry-run</button>
                <button onClick={() => compress(span.start_ref, span.end_ref)}>Compress</button>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel-section">
          <h3>Folds</h3>
          <ul>
            {folds.map(fold => (
              <li key={fold.id}>
                {fold.start_ref} - {fold.end_ref} ({fold.token_count} tokens)
                <button onClick={() => decompress(fold.id)}>Decompress</button>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel-section">
          <h3>Messages</h3>
          <ul>
            {messages.slice(0, 20).map(msg => (
              <li key={msg.ref}>
                [{msg.ref}] {msg.role}: {msg.content.slice(0, 80)}... ({msg.token_count} tok)
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="search-section">
        <h3>Search Context</h3>
        <input
          type="text"
          placeholder="Search query"
          onKeyDown={e => e.key === 'Enter' && search(e.currentTarget.value)}
        />
      </div>
    </section>
  )
}