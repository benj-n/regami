import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useWebSocket } from '../context/WebSocketContext'
import { apiGet } from '../services/api'

const Navbar: React.FC = () => {
  const { logout } = useAuth()
  const { connected } = useWebSocket()
  const [email, setEmail] = useState<string>('')

  useEffect(() => {
    let ignore = false
    apiGet<any>('/users/me').then(u => {
      if (!ignore) setEmail(u.email)
    }).catch(() => {})
    return () => { ignore = true }
  }, [])

  return (
    <nav style={{ padding: '8px 12px', background: '#0ea5e9', color: 'white' }}>
      <Link to="/profile" style={{ color: 'white', marginRight: 12 }}>Profil</Link>
      <Link to="/offers" style={{ color: 'white', marginRight: 12 }}>Offres</Link>
      <Link to="/requests" style={{ color: 'white', marginRight: 12 }}>Demandes</Link>
      <Link to="/messages" style={{ color: 'white', marginRight: 12 }}>Messages</Link>
      <Link to="/notifications" style={{ color: 'white', marginRight: 12 }}>Notifications</Link>
      <Link to="/dogs" style={{ color: 'white', marginRight: 12 }}>Chiens</Link>

      <span style={{ float: 'right', display: 'flex', alignItems: 'center', gap: 12 }}>
        {connected && (
          <span style={{ fontSize: '0.9em', opacity: 0.9 }} title="Notifications temps réel actives">
            ● En direct
          </span>
        )}
        {email && <span>{email}</span>}
        <button onClick={logout} style={{ background: 'white', color: '#0ea5e9', border: 'none', padding: '6px 10px', borderRadius: 4, cursor: 'pointer' }}>Se déconnecter</button>
      </span>
    </nav>
  )
}

export default Navbar
