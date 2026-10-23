import { useState, useEffect } from 'react'
import { SessionDashboard } from './components/SessionDashboard'
import { CompressionPanel } from './components/CompressionPanel'
import { AuthProvider, useAuth } from './hooks/useAuth'
import './App.css'

function AppContent() {
  const { user, login, logout, loading } = useAuth()

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  if (!user) {
    return <LoginForm onLogin={login} />
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Orbit Observatory</h1>
        <div className="user-info">
          <span>{user.username} ({user.roles.join(', ')})</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>
      <main className="main">
        <SessionDashboard />
        <CompressionPanel />
      </main>
    </div>
  )
}

function LoginForm({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await onLogin(username, password)
    } catch (err) {
      setError('Login failed')
    }
  }

  return (
    <div className="login-container">
      <h2>Login to Orbit Observatory</h2>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div>
          <label>Username: <input type="text" value={username} onChange={e => setUsername(e.target.value)} required /></label>
        </div>
        <div>
          <label>Password: <input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}