import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { useAuth } from './AuthContext'
import { useToast } from './ToastContext'
import { API_BASE } from '../env'

// Convert HTTP URL to WebSocket URL
const API_WS_BASE = API_BASE.replace(/^http/, 'ws')

type WebSocketMessage = {
  type: 'connected' | 'pong' | 'new_match' | 'match_accepted' | 'match_confirmed' | 'match_rejected' | 'new_message' | 'notification'
  data: any
  timestamp: number
}

type WebSocketContextType = {
  connected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: any) => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider')
  }
  return context
}

// Helper to get JWT token from cookie
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null
  return null
}

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth()
  const { push } = useToast()
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const pingIntervalRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    if (!isAuthenticated) {
      console.log('WebSocket: Not authenticated, skipping connection')
      return
    }

    // Get JWT token from cookie
    const token = getCookie('access_token')
    if (!token) {
      console.log('WebSocket: No access token cookie found')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket: Already connected')
      return
    }

    try {
      console.log('WebSocket: Connecting...')
      const ws = new WebSocket(`${API_WS_BASE}/ws?token=${token}`)

      ws.onopen = () => {
        console.log('WebSocket: Connected')
        setConnected(true)

        // Start ping interval to keep connection alive
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // Ping every 30 seconds
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          console.log('WebSocket message:', message.type, message.data)
          setLastMessage(message)

          // Handle different message types
          switch (message.type) {
            case 'connected':
              push('Connexion temps réel établie')
              break
            case 'new_match':
              push(`Nouveau match disponible !`, { type: 'success' })
              // Could trigger a sound notification here
              break
            case 'match_accepted':
              push(`Match accepté par ${message.data.requester_email}`, { type: 'success' })
              break
            case 'match_confirmed':
              push(`Match confirmé ! ✓`, { type: 'success' })
              break
            case 'match_rejected':
              push(`Match refusé`, { type: 'info' })
              break
            case 'new_message':
              push(`💬 Nouveau message de ${message.data.sender_email}`, { type: 'info' })
              break
            case 'notification':
              push(message.data.message, { type: 'info' })
              break
          }
        } catch (error) {
          console.error('WebSocket: Error parsing message', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket: Error', error)
        setConnected(false)
      }

      ws.onclose = () => {
        console.log('WebSocket: Disconnected')
        setConnected(false)

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // Attempt to reconnect after 5 seconds
        if (isAuthenticated) {
          console.log('WebSocket: Scheduling reconnect in 5s...')
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect()
          }, 5000)
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('WebSocket: Connection error', error)
      setConnected(false)
    }
  }, [isAuthenticated, push])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setConnected(false)
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket: Cannot send message, not connected')
    }
  }, [])

  // Connect/disconnect based on authentication
  useEffect(() => {
    if (isAuthenticated) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [isAuthenticated, connect, disconnect])

  return (
    <WebSocketContext.Provider value={{ connected, lastMessage, sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  )
}
