import React, { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'

// Validation schema
const loginSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
})

type LoginFormData = z.infer<typeof loginSchema>

const Login: React.FC = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation() as any
  const { login, loading } = useAuth()

  const onSubmit = handleSubmit(async (data) => {
    setError('')
    try {
      await login(data.email, data.password)
      const dest = location.state?.from?.pathname || '/profile'
      navigate(dest)
    } catch (e: any) {
      setError(e.message || 'Erreur de connexion')
    }
  })

  return (
    <div className="container">
      <h1>Connexion</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={onSubmit}>
        <label>
          Courriel
          <input type="email" {...register('email')} />
        </label>
        {errors.email && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.email.message}</p>}

        <label>
          Mot de passe
          <input type="password" {...register('password')} />
        </label>
        {errors.password && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.password.message}</p>}

        <button type="submit" disabled={loading || isSubmitting}>
          {loading || isSubmitting ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
      <p>
        <Link to="/forgot-password">Mot de passe oublie?</Link>
      </p>
      <p>
        Pas de compte? <a href="/register">Créer un compte</a>
      </p>
      <p>
        <Link to="/">Accueil</Link>
      </p>
    </div>
  )
}

export default Login
