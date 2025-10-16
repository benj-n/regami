import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { API_BASE } from '../env'
import MapPicker, { LatLng as LatLngT } from '../components/MapPicker'

// Validation schema
const registerSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
  dog_name: z.string().regex(/^[A-Z0-9]{1,98}[0-9]{2}$/, 'Format invalide: MAJUSCULES/CHIFFRES terminé par 2 chiffres').optional().or(z.literal('')),
})

type RegisterFormData = z.infer<typeof registerSchema>

const Register: React.FC = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [coord, setCoord] = useState<LatLngT | null>(null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [progress, setProgress] = useState<number>(0)
  const navigate = useNavigate()

  const onSubmit = handleSubmit(async (data) => {
    setError(''); setOk(''); setProgress(0)

    // Validate file (optional)
    if (file) {
      if (!file.type.startsWith('image/')) { setError('Le fichier doit être une image'); return }
      const maxBytes = 10 * 1024 * 1024
      if (file.size > maxBytes) { setError('Image trop volumineuse (max 10 Mo)'); return }
    }

    try {
      const fd = new FormData()
      fd.append('email', data.email)
      fd.append('password', data.password)
      if (data.dog_name) fd.append('dog_name', data.dog_name.toUpperCase())
      if (coord) {
        fd.append('location_lat', String(coord.lat))
        fd.append('location_lng', String(coord.lng))
      }
      if (file) fd.append('file', file, file.name)

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', `${API_BASE}/auth/register-multipart`)
        xhr.upload.onprogress = (evt) => {
          if (evt.lengthComputable) setProgress(Math.round((evt.loaded / evt.total) * 100))
        }
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve()
          else reject(new Error(xhr.responseText || 'Erreur'))
        }
        xhr.onerror = () => reject(new Error('Erreur réseau'))
        xhr.send(fd)
      })

      setOk('Compte créé, vous pouvez vous connecter.')
      setTimeout(() => navigate('/login'), 1000)
    } catch (e: any) {
      setError(e.message || 'Erreur')
    }
  })

  return (
    <div className="container">
      <h1>Inscription</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {ok && <p style={{ color: 'green' }}>{ok}</p>}
      <form onSubmit={onSubmit}>
        <label>Courriel</label>
        <input type="email" {...register('email')} />
        {errors.email && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.email.message}</p>}

        <label>Mot de passe</label>
        <input type="password" {...register('password')} />
        {errors.password && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.password.message}</p>}

        <h3>Profil</h3>
        <label>Nom du chien (optionnel)</label>
        <input
          {...register('dog_name')}
          placeholder="ex: REX21"
          title="MAJUSCULES/CHIFFRES et se termine par 2 chiffres"
          style={{ textTransform: 'uppercase' }}
        />
        {errors.dog_name && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.dog_name.message}</p>}
        <label>Photo du chien (optionnel)</label>
        <input type="file" accept="image/*" onChange={e => {
          const f = e.target.files?.[0] || null
          setFile(f)
          if (f) setPreview(URL.createObjectURL(f))
          else setPreview(null)
        }} />
        {preview && (
          <div style={{ marginTop: 8 }}>
            <img src={preview} alt="aperçu" style={{ maxHeight: 240, objectFit: 'contain', borderRadius: 6 }} />
          </div>
        )}
        <h3>Localisation</h3>
        <p>Cliquez sur la carte pour définir vos coordonnées.</p>
        <MapPicker value={coord} onChange={setCoord} />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Création en cours…' : 'Créer un compte'}
        </button>
        {isSubmitting && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
            <span className="spinner" aria-label="chargement" />
            <span>Envoi en cours… {progress}%</span>
          </div>
        )}
      </form>
      <p><Link to="/login">Déjà inscrit ? Se connecter</Link></p>
    </div>
  )
}

export default Register
