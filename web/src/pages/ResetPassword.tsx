import React, { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { API_BASE } from '../env'

// Validation schema
const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caracteres'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Les mots de passe ne correspondent pas',
  path: ['confirmPassword'],
})

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>

const ResetPassword: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  })
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const onSubmit = handleSubmit(async (data) => {
    setError('')
    try {
      const response = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: token,
          new_password: data.password,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to reset password')
      }

      setSuccess(true)

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (e: any) {
      setError(e.message || 'Une erreur est survenue')
    }
  })

  if (!token) {
    return (
      <div className="container">
        <h1>Lien invalide</h1>
        <p>Le lien de reinitialisation est invalide ou incomplet.</p>
        <p>
          <Link to="/forgot-password">Demander un nouveau lien</Link>
        </p>
      </div>
    )
  }

  if (success) {
    return (
      <div className="container">
        <h1>Mot de passe reinitialise</h1>
        <div style={{
          backgroundColor: '#d4edda',
          border: '1px solid #c3e6cb',
          borderRadius: '4px',
          padding: '1rem',
          marginBottom: '1rem'
        }}>
          <p style={{ margin: 0, color: '#155724' }}>
            Votre mot de passe a ete reinitialise avec succes.
          </p>
        </div>
        <p>
          Vous allez etre redirige vers la page de connexion...
        </p>
        <p>
          <Link to="/login">Se connecter maintenant</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="container">
      <h1>Reinitialiser le mot de passe</h1>
      <p>Entrez votre nouveau mot de passe.</p>

      {error && (
        <div style={{
          backgroundColor: '#f8d7da',
          border: '1px solid #f5c6cb',
          borderRadius: '4px',
          padding: '1rem',
          marginBottom: '1rem'
        }}>
          <p style={{ margin: 0, color: '#721c24' }}>{error}</p>
        </div>
      )}

      <form onSubmit={onSubmit}>
        <label>Nouveau mot de passe</label>
        <input type="password" {...register('password')} />
        {errors.password && (
          <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {errors.password.message}
          </p>
        )}

        <label>Confirmer le mot de passe</label>
        <input type="password" {...register('confirmPassword')} />
        {errors.confirmPassword && (
          <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {errors.confirmPassword.message}
          </p>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Reinitialisation...' : 'Reinitialiser le mot de passe'}
        </button>
      </form>

      <p>
        <Link to="/login">Retour a la connexion</Link>
      </p>
    </div>
  )
}

export default ResetPassword
