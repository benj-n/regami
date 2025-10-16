import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import { useAuth } from '../context/AuthContext'

const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  // Show loading while checking auth status
  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Chargement...</div>
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return (
    <>
      <Navbar />
      <Outlet />
    </>
  )
}

export default ProtectedRoute
