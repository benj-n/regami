import React, { lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { WebSocketProvider } from './context/WebSocketContext'
import ProtectedRoute from './components/ProtectedRoute'
import './i18n' // Initialize i18n
import './styles.css'

// Lazy load pages for better code splitting
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'))
const ResendVerification = lazy(() => import('./pages/ResendVerification'))
const Profile = lazy(() => import('./pages/Profile'))
const Offers = lazy(() => import('./pages/Offers'))
const Requests = lazy(() => import('./pages/Requests'))
const Notifications = lazy(() => import('./pages/Notifications'))
const Dogs = lazy(() => import('./pages/Dogs'))
const Messages = lazy(() => import('./pages/Messages'))

// Loading fallback component
const LoadingFallback = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: '18px',
    color: '#666'
  }}>
    Loading...
  </div>
)

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <AuthProvider>
        <WebSocketProvider>
          <BrowserRouter>
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password/:token" element={<ResetPassword />} />
                <Route path="/verify-email/:token" element={<VerifyEmail />} />
                <Route path="/resend-verification" element={<ResendVerification />} />

                <Route element={<ProtectedRoute />}>
                  <Route path="/" element={<Navigate to="/profile" replace />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/dogs" element={<Dogs />} />
                  <Route path="/offers" element={<Offers />} />
                  <Route path="/requests" element={<Requests />} />
                  <Route path="/messages" element={<Messages />} />
                  <Route path="/notifications" element={<Notifications />} />
                </Route>

                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </WebSocketProvider>
      </AuthProvider>
    </ToastProvider>
  </React.StrictMode>
)
