import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiGet, apiPut, apiDeleteVoid, apiPost } from '../services/api'
import MapPicker, { LatLng as LatLngT } from '../components/MapPicker'
import LoadingSpinner from '../components/LoadingSpinner'
import LoadingButton from '../components/LoadingButton'

const Profile: React.FC = () => {
  const { logout } = useAuth()
  const [me, setMe] = useState<any>(null)
  const [coord, setCoord] = useState<LatLngT | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [resendingVerification, setResendingVerification] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        setError('')
        const data = await apiGet<any>('/users/me')
        setMe(data)
        if (typeof data.location_lat === 'number' && typeof data.location_lng === 'number') {
          setCoord({ lat: data.location_lat, lng: data.location_lng })
        } else {
          setCoord(null)
        }
      } catch (e: any) {
        setError(e.message || 'Erreur lors du chargement du profil')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function save() {
    try {
      setSaving(true)
      setError('')
      setMessage('')
      const payload: any = {}
      if (coord) { payload.location_lat = coord.lat; payload.location_lng = coord.lng }
      const data = await apiPut<any>('/users/me', payload)
      setMe(data)
      setMessage('Sauvegardé!')
      setTimeout(() => setMessage(''), 1500)
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteAccount() {
    try {
      setDeleting(true)
      setError('')
      await apiDeleteVoid('/users/me')
      // Logout will redirect to login page
      logout()
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la suppression du compte')
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  async function handleResendVerification() {
    try {
      setResendingVerification(true)
      setError('')
      setMessage('')
      await apiPost('/auth/resend-verification', { email: me.email })
      setMessage('Email de verification envoye! Verifiez votre boite de reception.')
      setTimeout(() => setMessage(''), 5000)
    } catch (e: any) {
      setError(e.message || 'Erreur lors de l\'envoi de l\'email')
    } finally {
      setResendingVerification(false)
    }
  }

  if (loading) return <LoadingSpinner fullPage text="Chargement du profil..." />
  if (error && !me) return (
    <div className="container">
      <p style={{ color: 'red' }}>{error}</p>
      <button onClick={() => window.location.reload()}>Réessayer</button>
    </div>
  )
  return (
    <div className="container">
      <h1>Mon profil</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {message && <p style={{ color: 'green' }}>{message}</p>}

      {/* Email Verification Status */}
      {!me.email_verified && (
        <div style={{
          backgroundColor: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '4px',
          padding: '1rem',
          marginBottom: '1rem'
        }}>
          <p style={{ margin: '0 0 0.5rem 0', fontWeight: 'bold', color: '#856404' }}>
            Votre email n'est pas verifie
          </p>
          <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#856404' }}>
            Veuillez verifier votre email pour profiter de toutes les fonctionnalites.
          </p>
          <LoadingButton
            onClick={handleResendVerification}
            loading={resendingVerification}
            loadingText="Envoi..."
            style={{
              backgroundColor: '#ffc107',
              color: '#212529',
              border: 'none',
              fontSize: '0.9rem',
              padding: '0.4rem 0.8rem'
            }}
          >
            Renvoyer l'email de verification
          </LoadingButton>
        </div>
      )}

      <p>
        Email: {me.email}
        {me.email_verified && (
          <span style={{
            marginLeft: '0.5rem',
            color: '#28a745',
            fontSize: '0.9rem'
          }}>
            (verifie)
          </span>
        )}
      </p>
      <h3>Localisation</h3>
      <p>Cliquez sur la carte pour ajuster vos coordonnées.</p>
      <MapPicker value={coord} onChange={setCoord} />
      <div>
        <LoadingButton onClick={save} loading={saving} loadingText="Enregistrement...">
          Enregistrer
        </LoadingButton>
        <button onClick={logout} style={{ marginLeft: 8 }}>Se déconnecter</button>
      </div>

      {/* Account Deletion Section */}
      <div style={{
        marginTop: '3rem',
        paddingTop: '2rem',
        borderTop: '1px solid #e0e0e0'
      }}>
        <h3 style={{ color: '#dc3545' }}>Zone dangereuse</h3>
        <p style={{ color: '#666', fontSize: '0.9rem' }}>
          La suppression de votre compte est permanente et irréversible.
          Toutes vos données seront supprimées.
        </p>

        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Supprimer mon compte
          </button>
        ) : (
          <div style={{
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '4px',
            padding: '1rem',
            marginTop: '1rem'
          }}>
            <p style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>
              Êtes-vous sûr de vouloir supprimer votre compte ?
            </p>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.9rem' }}>
              Cette action supprimera définitivement votre compte, vos chiens,
              vos messages et toutes vos données.
            </p>
            <div>
              <LoadingButton
                onClick={handleDeleteAccount}
                loading={deleting}
                loadingText="Suppression..."
                style={{
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  marginRight: '0.5rem'
                }}
              >
                Oui, supprimer mon compte
              </LoadingButton>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                style={{
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Profile
