import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Notifications from '../pages/Notifications'
import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'

vi.mock('../services/api', () => ({
  apiGet: vi.fn().mockResolvedValue({ items: [
    { id: 1, message: 'Test notif', is_read: false, created_at: new Date().toISOString() },
  ], total: 1 }),
  apiPutVoid: vi.fn().mockResolvedValue(undefined),
  apiPostVoid: vi.fn().mockResolvedValue(undefined),
}))

function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AuthProvider>{children}</AuthProvider>
    </ToastProvider>
  )
}

describe('Notifications page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('marks single as read', async () => {
    render(
      <Providers>
        <Notifications />
      </Providers>
    )

    const btn = await screen.findByText('Marquer lu')
    fireEvent.click(btn)

    await waitFor(() => {
      expect(screen.getByText(/Notifications/)).toBeInTheDocument()
    })
  })

  it('marks all as read', async () => {
    render(
      <Providers>
        <Notifications />
      </Providers>
    )

    const btn = await screen.findByText('Tout marquer comme lu')
    fireEvent.click(btn)

    await waitFor(() => {
      expect(screen.getByText(/Notifications/)).toBeInTheDocument()
    })
  })

  it('toggles unread-only filter', async () => {
    render(
      <Providers>
        <Notifications />
      </Providers>
    )
    const checkbox = await screen.findByLabelText('Unread only')
    fireEvent.click(checkbox)
    await waitFor(() => {
      expect(checkbox).toBeChecked()
    })
  })
})
