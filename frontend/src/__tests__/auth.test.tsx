import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './hooks/useAuth'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { headers: { common: {} } },
  },
}))

import axios from 'axios'

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('provides login function', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    axios.post.mockResolvedValueOnce({ data: { access_token: 'token', refresh_token: 'refresh' } })
    axios.get.mockResolvedValueOnce({ data: mockUser })

    function TestComponent() {
      const { login, user, loading } = useAuth()
      return (
        <div>
          <span data-testid="loading">{loading ? 'true' : 'false'}</span>
          <span data-testid="user">{user ? user.username : 'null'}</span>
          <button onClick={() => login('test', 'pass')}>Login</button>
        </div>
      )
    }

    render(<AuthProvider><TestComponent /></AuthProvider>)

    expect(screen.getByTestId('loading')).toHaveTextContent('true')

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/login', { username: 'test', password: 'pass' })
      expect(localStorage.getItem('access_token')).toBe('token')
    })
  })

  it('loads user from stored token on mount', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    localStorage.setItem('access_token', 'stored-token')
    axios.get.mockResolvedValueOnce({ data: mockUser })

    function TestComponent() {
      const { user, loading } = useAuth()
      return (
        <div>
          <span data-testid="loading">{loading ? 'true' : 'false'}</span>
          <span data-testid="user">{user ? user.username : 'null'}</span>
        </div>
      )
    }

    render(<AuthProvider><TestComponent /></AuthProvider>)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
      expect(screen.getByTestId('user')).toHaveTextContent('test')
    })

    expect(axios.defaults.headers.common['Authorization']).toBe('Bearer stored-token')
  })

  it('clears user on logout', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    localStorage.setItem('access_token', 'stored-token')
    axios.get.mockResolvedValueOnce({ data: mockUser })

    function TestComponent() {
      const { user, logout, loading } = useAuth()
      return (
        <div>
          <span data-testid="user">{user ? user.username : 'null'}</span>
          <button onClick={logout}>Logout</button>
        </div>
      )
    }

    render(<AuthProvider><TestComponent /></AuthProvider>)

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('test')
    })

    fireEvent.click(screen.getByText('Logout'))

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(screen.getByTestId('user')).toHaveTextContent('null')
  })
})