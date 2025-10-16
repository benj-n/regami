import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Offers from '../pages/Offers'
import * as apiMod from '../services/api'
import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'

// Mock API functions
vi.mock('../services/api', () => ({
  apiPost: vi.fn().mockResolvedValue({ id: 1 }),
  apiGet: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 }),
  apiDeleteVoid: vi.fn().mockResolvedValue(undefined),
}))

function Providers({ children }: { children: React.ReactNode }) {
  // Token isn't required because we mock API calls; AuthProvider still needed to satisfy component hooks
  return (
    <ToastProvider>
      <AuthProvider>{children}</AuthProvider>
    </ToastProvider>
  )
}

describe('Offers page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates an offer and reloads list', async () => {
    render(
      <Providers>
        <Offers />
      </Providers>
    )

    const start = screen.getByLabelText('Début') as HTMLInputElement
    const end = screen.getByLabelText('Fin') as HTMLInputElement
    fireEvent.change(start, { target: { value: '2025-10-16T10:00' } })
    fireEvent.change(end, { target: { value: '2025-10-16T12:00' } })

    const publish = screen.getByText('Publier une offre')
    fireEvent.click(publish)

    await waitFor(() => {
      expect(screen.getByText(/Mes offres/)).toBeInTheDocument()
    })
  })

  it('supports delete within list', async () => {
    ;(apiMod.apiGet as any).mockResolvedValueOnce({ items: [
      { id: 10, start_at: new Date('2025-10-16T10:00:00Z').toISOString(), end_at: new Date('2025-10-16T12:00:00Z').toISOString() },
    ], total: 1, page: 1, page_size: 10 })
    render(
      <Providers>
        <Offers />
      </Providers>
    )
    const deleteBtn = await screen.findByText('Supprimer')
    fireEvent.click(deleteBtn)
    await waitFor(() => expect(apiMod.apiDeleteVoid).toHaveBeenCalled())
  })
})
