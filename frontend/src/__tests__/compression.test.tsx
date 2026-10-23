import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CompressionPanel } from '../components/CompressionPanel'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import axios from 'axios'

describe('CompressionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads session and displays compressible spans', async () => {
    axios.get
      .mockResolvedValueOnce({ data: [] }) // messages
      .mockResolvedValueOnce({ data: [] }) // folds
    axios.post.mockResolvedValueOnce({ data: { compressible_spans: [
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
    axios.get.mockRejectedValueOnce(new Error('Network error'))

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('Failed to load session')).toBeInTheDocument()
    })
  })

  it('calls compress endpoint on Compress button', async () => {
    axios.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [] })
    axios.post
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

    fireEvent.click(screen.getByText('Compress'))

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/compress', {
        session_id: 'test-session',
        start_ref: 'm00001',
        end_ref: 'm00005',
        dry_run: false,
      })
    })
  })

  it('calls decompress endpoint', async () => {
    axios.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ id: 'fold-1', start_ref: 'm00001', end_ref: 'm00005', token_count: 100 }] })
    axios.post.mockResolvedValueOnce({ data: { compressible_spans: [] } })
    axios.post.mockResolvedValueOnce({ data: { content: 'Decompressed content' } })

    render(<CompressionPanel />)

    fireEvent.change(screen.getByPlaceholderText('Session ID'), { target: { value: 'test-session' } })
    fireEvent.click(screen.getByText('Load Session'))

    await waitFor(() => {
      expect(screen.getByText('Decompress')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Decompress'))

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith('/api/decompress', {
        session_id: 'test-session',
        ref: 'fold-1',
      })
    })
  })
})