import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CompressionPanel } from '../components/CompressionPanel'
import type { Mock } from 'vitest'

// Mock axios using vi.hoisted to avoid hoisting issues
const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    get: mockGet,
    post: mockPost,
  },
}))

describe('CompressionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads session and displays compressible spans', async () => {
    ;(mockGet as Mock)
      .mockResolvedValueOnce({ data: [] }) // messages
      .mockResolvedValueOnce({ data: [] }) // folds
    ;(mockPost as Mock).mockResolvedValueOnce({ data: { compressible_spans: [
      { start_ref: 'm00001', end_ref: 'm00005', token_count: 100 }
    ] } }) // acp_status

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('m00001 - m00005 (100 tokens)')).toBeInTheDocument()
    })

    expect(screen.getByText('Dry-run')).toBeInTheDocument()
    expect(screen.getByText('Compress')).toBeInTheDocument()
  })

  it('shows error on load failure', async () => {
    ;(mockGet as Mock).mockRejectedValueOnce(new Error('Network error'))

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('Failed to load session')).toBeInTheDocument()
    })
  })

  it('calls compress endpoint on Compress button', async () => {
    ;(mockGet as Mock)
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
    ;(mockPost as Mock)
      .mockResolvedValueOnce({ data: { compressible_spans: [
        { start_ref: 'm00001', end_ref: 'm00005', token_count: 100 }
      ] } })
      .mockResolvedValueOnce({ data: { success: true, folded_refs: ['m00001', 'm00002'] } })

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('Dry-run')).toBeInTheDocument()
    })

    // Click the Compress button on the first span row
    fireEvent.click(screen.getByText('Compress'))

    await waitFor(() => {
      expect(screen.getByText('Compressed successfully')).toBeInTheDocument()
    })

    expect(mockPost).toHaveBeenCalledWith('/api/compress', expect.objectContaining({
      session_id: 'test-session',
      start_ref: 'm00001',
      end_ref: 'm00005',
      dry_run: false,
    }))
  })

  it('calls decompress endpoint', async () => {
    ;(mockGet as Mock)
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [
        { id: 'fold-123', start_ref: 'm00001', end_ref: 'm00005', summary: 'Test fold', token_count: 100 }
      ] })
    ;(mockPost as Mock)
      .mockResolvedValueOnce({ data: { compressible_spans: [
        { start_ref: 'm00001', end_ref: 'm00005', token_count: 100 }
      ] } })
      .mockResolvedValueOnce({ data: { success: true, content: 'Decompressed content' } })

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('Dry-run')).toBeInTheDocument()
    })

    // Click the Decompress button on the first fold row
    fireEvent.click(screen.getByText('Decompress'))

    // Verify the API call was made (alert is not testable in jsdom)
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/decompress', expect.objectContaining({
        session_id: 'test-session',
        ref: 'fold-123',
      }))
    })
  })
})
