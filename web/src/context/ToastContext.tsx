import React, { createContext, useContext, useCallback, useState, useEffect } from 'react'

type Toast = { id: number; message: string; type?: 'info' | 'success' | 'error'; timeout?: number }

interface ToastContextValue {
  push: (message: string, opts?: { type?: 'info' | 'success' | 'error'; timeout?: number }) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const push = useCallback((message: string, opts?: { type?: 'info' | 'success' | 'error'; timeout?: number }) => {
    const id = Date.now() + Math.random()
    const toast: Toast = { id, message, type: opts?.type ?? 'info', timeout: opts?.timeout ?? 3000 }
    setToasts(prev => [...prev, toast])
  }, [])

  useEffect(() => {
    const timers = toasts.map(t => setTimeout(() => setToasts(prev => prev.filter(x => x.id !== t.id)), t.timeout ?? 3000))
    return () => { timers.forEach(clearTimeout) }
  }, [toasts])

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div style={{ position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', gap: 8, zIndex: 1000 }}>
        {toasts.map(t => (
          <div key={t.id} style={{ background: t.type === 'error' ? '#ef4444' : t.type === 'success' ? '#22c55e' : '#0ea5e9', color: 'white', padding: '8px 12px', borderRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
