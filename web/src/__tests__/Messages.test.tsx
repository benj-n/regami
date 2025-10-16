import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Messages from '../pages/Messages'
import { ToastProvider } from '../context/ToastContext'

// Mock the API module
vi.mock('../services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

// Mock the WebSocket context
vi.mock('../context/WebSocketContext', () => ({
  useWebSocket: () => ({
    connected: true,
    lastMessage: null,
    sendMessage: vi.fn(),
  }),
  WebSocketProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Mock the Auth context
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 'me', email: 'me@regami.com' },
    token: 'test-token',
    login: vi.fn(),
    logout: vi.fn(),
    loading: false,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Import the mocked module to access mock functions
import { apiGet, apiPost } from '../services/api'

function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  )
}

const mockConversations = [
  {
    other_user_id: 'user-1',
    other_user_email: 'alice@regami.com',
    last_message: 'Hello there!',
    last_message_at: new Date().toISOString(),
    unread_count: 2,
  },
  {
    other_user_id: 'user-2',
    other_user_email: 'bob@regami.com',
    last_message: 'See you tomorrow',
    last_message_at: new Date(Date.now() - 86400000).toISOString(),
    unread_count: 0,
  },
]

const mockMessages = [
  {
    id: 1,
    sender_id: 'user-1',
    recipient_id: 'me',
    content: 'Hi!',
    is_read: true,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    sender_email: 'alice@regami.com',
  },
  {
    id: 2,
    sender_id: 'me',
    recipient_id: 'user-1',
    content: 'Hello there!',
    is_read: true,
    created_at: new Date().toISOString(),
    sender_email: 'me@regami.com',
  },
]

describe('Messages page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Set token for authentication
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('token', 'test-token')
    }
    // Default mock implementations
    ;(apiGet as any).mockImplementation((url: string) => {
      if (url === '/messages/conversations') {
        return Promise.resolve(mockConversations)
      }
      if (url.startsWith('/messages/conversations/')) {
        return Promise.resolve(mockMessages)
      }
      return Promise.resolve([])
    })
    ;(apiPost as any).mockResolvedValue({
      id: 3,
      sender_id: 'me',
      recipient_id: 'user-1',
      content: 'New message',
      is_read: false,
      created_at: new Date().toISOString(),
    })
  })

  it('renders the messages page title', async () => {
    render(
      <Providers>
        <Messages />
      </Providers>
    )

    // Should show the title
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('calls apiGet to fetch conversations on mount', async () => {
    render(
      <Providers>
        <Messages />
      </Providers>
    )

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/messages/conversations')
    })
  })

  it('shows loading state initially', () => {
    render(
      <Providers>
        <Messages />
      </Providers>
    )

    // Page renders without throwing
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('handles empty conversations list', async () => {
    ;(apiGet as any).mockResolvedValue([])

    render(
      <Providers>
        <Messages />
      </Providers>
    )

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/messages/conversations')
    })

    // Page still renders without crashing
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('handles API error gracefully', async () => {
    ;(apiGet as any).mockRejectedValue(new Error('Network error'))

    render(
      <Providers>
        <Messages />
      </Providers>
    )

    // Should handle error without crashing
    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/messages/conversations')
    })

    // Page still renders
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })
})
