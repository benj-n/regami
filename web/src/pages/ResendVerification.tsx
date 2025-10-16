import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { API_BASE } from '../env'

// Validation schema
const resendSchema = z.object({
  email: z.string().email('Email invalide'),
})

type ResendFormData = z.infer<typeof resendSchema>

const ResendVerification: React.FC = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ResendFormData>({
    resolver: zodResolver(resendSchema),
  })
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const onSubmit = handleSubmit(async (data) => {
    setError('')
    setSuccess(false)
    try {
      const response = await fetch(`${API_BASE}/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: data.email }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send verification email')
      }

      setSuccess(true)
    } catch (e: any) {
      setError(e.message || 'Une erreur est survenue')
    }
  })

  if (success) {
    return (
      <div className="container">
        <h1>Email envoye</h1>
        <div style={{
          backgroundColor: '#d4edda',
          border: '1px solid #c3e6cb',
          borderRadius: '4px',
          padding: '1rem',
          marginBottom: '1rem'
        }}>
          <p style={{ margin: 0, color: '#155724' }}>
            Si un compte existe avec cette adresse email et n'est pas encore verifie,
            vous recevrez un nouveau lien de verification.
          </p>
        </div>
        <p>
          Verifiez votre boite de reception et vos spams.
        </p>
        <p>
          <Link to="/login">Retour a la connexion</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="container">
      <h1>Renvoyer le lien de verification</h1>
      <p>Entrez votre adresse email pour recevoir un nouveau lien de verification.</p>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={onSubmit}>
        <label>Courriel</label>
        <input type="email" {...register('email')} placeholder="votre@email.com" />
        {errors.email && (
          <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {errors.email.message}
          </p>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Envoi en cours...' : 'Envoyer le lien'}
        </button>
      </form>

      <p>
        <Link to="/login">Retour a la connexion</Link>
      </p>
    </div>
  )
}

export default ResendVerification
