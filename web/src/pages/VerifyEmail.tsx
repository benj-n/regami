import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { API_BASE } from '../env'
import LoadingSpinner from '../components/LoadingSpinner'

const VerifyEmail: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Lien de verification invalide ou incomplet.')
      return
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/verify-email/${token}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })

        const data = await response.json()

        if (response.ok) {
          setStatus('success')
          setMessage(data.message || 'Votre email a ete verifie avec succes!')
        } else {
          setStatus('error')
          setMessage(data.detail || 'Erreur lors de la verification.')
        }
      } catch (e) {
        setStatus('error')
        setMessage('Une erreur est survenue. Veuillez reessayer.')
      }
    }

    verifyEmail()
  }, [token])

  if (status === 'loading') {
    return <LoadingSpinner fullPage text="Verification de votre email..." />
  }

  return (
    <div className="container">
      {status === 'success' ? (
        <>
          <h1 style={{ color: '#28a745' }}>Email verifie!</h1>
          <div style={{
            backgroundColor: '#d4edda',
            border: '1px solid #c3e6cb',
            borderRadius: '4px',
            padding: '1rem',
            marginBottom: '1rem'
          }}>
            <p style={{ margin: 0, color: '#155724' }}>{message}</p>
          </div>
          <p>
            Vous pouvez maintenant profiter de toutes les fonctionnalites de Regami.
          </p>
          <p>
            <Link to="/login">
              <button>Se connecter</button>
            </Link>
          </p>
        </>
      ) : (
        <>
          <h1 style={{ color: '#dc3545' }}>Erreur de verification</h1>
          <div style={{
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '4px',
            padding: '1rem',
            marginBottom: '1rem'
          }}>
            <p style={{ margin: 0, color: '#721c24' }}>{message}</p>
          </div>
          <p>
            Si vous n'avez pas encore verifie votre email, vous pouvez demander un nouveau lien de verification.
          </p>
          <p>
            <Link to="/resend-verification">Renvoyer le lien de verification</Link>
          </p>
          <p>
            <Link to="/login">Retour a la connexion</Link>
          </p>
        </>
      )}
    </div>
  )
}

export default VerifyEmail
