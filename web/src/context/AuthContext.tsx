import React, { createContext, useContext, useEffect, useState } from 'react'
import { API_BASE } from '../env'

interface AuthContextValue {
  isAuthenticated: boolean
  userId: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
  setToast: (msg: string) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)


export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Track authentication state (cookie-based, no token in state)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userId, setUserId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState('')

  // Check authentication status on mount
  useEffect(() => {
    checkAuth()
  }, [])

  async function checkAuth() {
    try {
      // Try to fetch current user to verify auth status
      const res = await fetch(`${API_BASE}/users/me`, {
        credentials: 'include', // Include cookies
      })
      if (res.ok) {
        const user = await res.json()
        setIsAuthenticated(true)
        setUserId(user.id)
      } else {
        setIsAuthenticated(false)
        setUserId(null)
      }
    } catch {
      setIsAuthenticated(false)
      setUserId(null)
    } finally {
      setLoading(false)
    }
  }

  async function login(email: string, password: string) {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: form,
        credentials: 'include', // Include cookies
      })
      if (!res.ok) throw new Error('Identifiants invalides')
      const data = await res.json()
      setIsAuthenticated(true)
      setUserId(data.user_id)
    } finally {
      setLoading(false)
    }
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Ignore errors during logout
    }
    setIsAuthenticated(false)
    setUserId(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, userId, login, logout, loading, setToast }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
