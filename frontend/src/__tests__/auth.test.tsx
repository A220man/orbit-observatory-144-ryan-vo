import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '../hooks/useAuth'
import type { Mock } from 'vitest'

// Mock axios using vi.hoisted to avoid hoisting issues
const { mockGet, mockPost, mockDefaults } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockDefaults: { headers: { common: {} as Record<string, string> } },
}))

vi.mock('axios', () => ({
  default: {
    get: mockGet,
    post: mockPost,
    defaults: mockDefaults,
  },
}))

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('provides login function', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    ;(mockPost as Mock).mockResolvedValueOnce({ data: { access_token: 'token', refresh_token: 'refresh' } })
    ;(mockGet as Mock).mockResolvedValueOnce({ data: mockUser })

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

    // No token stored, so loading should become false after effect
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('null')

    fireEvent.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/login', { username: 'test', password: 'pass' })
      expect(localStorage.getItem('access_token')).toBe('token')
    })
  })

  it('loads user from stored token on mount', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    localStorage.setItem('access_token', 'stored-token')
    ;(mockGet as Mock).mockResolvedValueOnce({ data: mockUser })

    function TestComponent() {
      const { user } = useAuth()
      return <span data-testid="user">{user ? user.username : 'null'}</span>
    }

    render(<AuthProvider><TestComponent /></AuthProvider>)

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('test')
    })

    expect(mockDefaults.headers.common['Authorization']).toBe('Bearer stored-token')
  })

  it('clears user on logout', async () => {
    const mockUser = { id: '1', username: 'test', email: 'test@test.com', roles: ['operator'] }
    localStorage.setItem('access_token', 'stored-token')
    localStorage.setItem('refresh_token', 'stored-refresh')
    ;(mockGet as Mock).mockResolvedValueOnce({ data: mockUser })

    function TestComponent() {
      const { user, logout } = useAuth()
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

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('null')
    })

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })
})
