import React, { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiDeleteVoid, apiGet, apiPost, apiUpload, apiPostVoid } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import LoadingButton from '../components/LoadingButton'

// Validation schema for creating a dog
const createDogSchema = z.object({
  name: z.string().regex(/^[A-Z0-9]{1,98}[0-9]{2}$/, 'Format invalide: MAJUSCULES/CHIFFRES terminé par 2 chiffres'),
  birth_month: z.number().int().min(1, 'Mois invalide').max(12, 'Mois invalide'),
  birth_year: z.number().int().min(1995, 'Année minimum: 1995').max(new Date().getFullYear(), 'Année invalide'),
  sex: z.enum(['male', 'female']),
})

type CreateDogFormData = z.infer<typeof createDogSchema>

type Dog = {
  id: number
  name: string
  photo_url?: string | null
  birth_month: number
  birth_year: number
  sex: 'male' | 'female'
  age_years: number
  created_at: string
  owner_name?: string
  distance_km?: number
}

type SearchResult = {
  items: Dog[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

const namePattern = /^[A-Z0-9]{1,98}[0-9]{2}$/

const Dogs: React.FC = () => {
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<CreateDogFormData>({
    resolver: zodResolver(createDogSchema),
    defaultValues: {
      name: '',
      birth_month: 1,
      birth_year: new Date().getFullYear(),
      sex: 'male',
    },
  })

  const { push } = useToast()
  const [dogs, setDogs] = useState<Dog[]>([])
  const [coOwnerUserId, setCoOwnerUserId] = useState('')
  const [loading, setLoading] = useState(true)
  const [uploadingIds, setUploadingIds] = useState<Set<number>>(new Set())
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set())
  const [error, setError] = useState('')

  // User location for search
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null)

  // Search state
  const [searchResults, setSearchResults] = useState<Dog[]>([])
  const [searchName, setSearchName] = useState('')
  const [searchRadiusKm, setSearchRadiusKm] = useState(10)
  const [searchPage, setSearchPage] = useState(1)
  const [searchTotal, setSearchTotal] = useState(0)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const load = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await apiGet<Dog[]>(`/dogs/me`)
      setDogs(data)

      // Also fetch user profile to get location
      try {
        const profile = await apiGet<any>('/users/me')
        if (profile.location_lat !== null && profile.location_lng !== null) {
          setUserLocation({ lat: profile.location_lat, lng: profile.location_lng })
        }
      } catch {
        // Location is optional, ignore error
      }
    } catch (e: any) {
      setError(e.message || 'Erreur lors du chargement des chiens')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const searchDogs = async () => {
    try {
      setSearchLoading(true)
      setSearchError('')
      setHasSearched(true)

      const params = new URLSearchParams({
        page: String(searchPage),
        page_size: '20',
      })

      if (searchName.trim()) {
        params.append('name', searchName.trim())
      }

      // Add location-based search if user has location set
      if (userLocation) {
        params.append('lat', String(userLocation.lat))
        params.append('lng', String(userLocation.lng))
        params.append('radius_km', String(searchRadiusKm))
      }

      const data = await apiGet<SearchResult>(`/dogs/search?${params}`)
      setSearchResults(data.items)
      setSearchTotal(data.total)
    } catch (e: any) {
      setSearchError(e.message || 'Erreur lors de la recherche')
    } finally {
      setSearchLoading(false)
    }
  }

  // Trigger search when page changes
  useEffect(() => {
    if (hasSearched) {
      searchDogs()
    }
  }, [searchPage])

  const resetSearch = () => {
    setSearchName('')
    setSearchRadiusKm(10)
    setSearchPage(1)
    setSearchResults([])
    setSearchTotal(0)
    setHasSearched(false)
    setSearchError('')
  }

  const createDog = handleSubmit(async (data) => {
    try {
      const created = await apiPost<Dog>(`/dogs/`, {
        name: data.name,
        birth_month: data.birth_month,
        birth_year: data.birth_year,
        sex: data.sex
      })
      push('Chien créé')
      reset() // Reset form to default values
      setDogs([created, ...dogs])
    } catch (e: any) {
      push(e.message || 'Erreur lors de la création')
    }
  })

  const removeDog = async (id: number) => {
    try {
      setDeletingIds(prev => new Set(prev).add(id))
      await apiDeleteVoid(`/dogs/${id}`)
      push('Chien supprimé')
      setDogs(dogs.filter((d: Dog) => d.id !== id))
    } catch (e: any) {
      push(e.message || 'Erreur lors de la suppression')
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const addCoOwner = async (dogId: number) => {
    if (!coOwnerUserId) { push('ID utilisateur requis'); return }
    await apiPostVoid(`/dogs/${dogId}/coowners/${coOwnerUserId}`)
    push('Co-propriétaire ajouté')
    setCoOwnerUserId('')
  }

  const removeCoOwner = async (dogId: number) => {
    if (!coOwnerUserId) { push('ID utilisateur requis'); return }
    await apiDeleteVoid(`/dogs/${dogId}/coowners/${coOwnerUserId}`)
    push('Co-propriétaire retiré')
    setCoOwnerUserId('')
  }

  const uploadPhoto = async (dogId: number, file: File | null) => {
    if (!file) return
    if (!file.type.startsWith('image/')) { push('Fichier image requis'); return }
    const maxBytes = 10 * 1024 * 1024
    if (file.size > maxBytes) { push('Image trop volumineuse (max 10 Mo)'); return }
    try {
      setUploadingIds(prev => new Set(prev).add(dogId))
      const fd = new FormData()
      fd.append('file', file, file.name)
      const updated = await apiUpload<Dog>(`/dogs/${dogId}/photo`, fd)
      push('Photo mise à jour')
      setDogs(dogs.map((d: Dog) => d.id === updated.id ? updated : d))
    } catch (e: any) {
      push(e.message || 'Erreur lors du téléchargement')
    } finally {
      setUploadingIds(prev => {
        const next = new Set(prev)
        next.delete(dogId)
        return next
      })
    }
  }

  if (loading) return <LoadingSpinner fullPage text="Chargement des chiens..." />

  if (error && dogs.length === 0) return (
    <div className="container">
      <p style={{ color: 'red' }}>{error}</p>
      <button onClick={load}>Réessayer</button>
    </div>
  )

  return (
    <div className="container">
        <h2>Mes chiens</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}

        <div className="card" style={{ marginBottom: 16 }}>
          <h3>Créer un chien</h3>
          <form onSubmit={createDog} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label>
                Nom (ex: REX21)
                <input
                  {...register('name')}
                  aria-label="Nom du chien"
                  placeholder="Nom"
                  disabled={isSubmitting}
                  style={{ marginLeft: 8, width: 200, textTransform: 'uppercase' }}
                />
              </label>
              {errors.name && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.name.message}</p>}
              <small style={{ display: 'block', marginTop: 4, color: '#666' }}>
                Format: MAJUSCULES/CHIFFRES et se termine par 2 chiffres
              </small>
            </div>

            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div>
                <label>
                  Mois de naissance
                  <select
                    {...register('birth_month', { valueAsNumber: true })}
                    disabled={isSubmitting}
                    style={{ marginLeft: 8 }}
                  >
                    <option value="1">Janvier</option>
                    <option value="2">Février</option>
                    <option value="3">Mars</option>
                    <option value="4">Avril</option>
                    <option value="5">Mai</option>
                    <option value="6">Juin</option>
                    <option value="7">Juillet</option>
                    <option value="8">Août</option>
                    <option value="9">Septembre</option>
                    <option value="10">Octobre</option>
                    <option value="11">Novembre</option>
                    <option value="12">Décembre</option>
                  </select>
                </label>
                {errors.birth_month && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.birth_month.message}</p>}
              </div>

              <div>
                <label>
                  Année de naissance
                  <input
                    type="number"
                    {...register('birth_year', { valueAsNumber: true })}
                    min="1995"
                    max={new Date().getFullYear()}
                    disabled={isSubmitting}
                    style={{ marginLeft: 8, width: 100 }}
                  />
                </label>
                {errors.birth_year && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.birth_year.message}</p>}
              </div>

              <div>
                <label>
                  Sexe
                  <select
                    {...register('sex')}
                    disabled={isSubmitting}
                    style={{ marginLeft: 8 }}
                  >
                    <option value="male">Mâle</option>
                    <option value="female">Femelle</option>
                  </select>
                </label>
                {errors.sex && <p style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.25rem' }}>{errors.sex.message}</p>}
              </div>
            </div>

            <div>
              <LoadingButton
                type="submit"
                loading={isSubmitting}
                loadingText="Création..."
              >
                Créer
              </LoadingButton>
            </div>
          </form>
        </div>

    <div className="list">
          {dogs.map(dog => (
            <div key={dog.id} className="list-item">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                {dog.photo_url ? (
                  <img src={dog.photo_url} alt={dog.name} style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6 }} />
                ) : (
                  <div style={{ width: 64, height: 64, background: '#eee', display: 'inline-block', borderRadius: 6 }} />
                )}
                <div>
                  <strong>{dog.name}</strong>
                  <div style={{ fontSize: '0.9em', color: '#666', marginTop: 4 }}>
                    {dog.sex === 'male' ? '♂ Mâle' : '♀ Femelle'} • {dog.age_years} {dog.age_years === 1 ? 'an' : 'ans'}
                  </div>
                </div>

                <label style={{ marginLeft: 12 }}>
                  Photo:
                  <input
                    type="file"
                    accept="image/*"
                    onChange={e => uploadPhoto(dog.id, e.target.files?.[0] ?? null)}
                    disabled={uploadingIds.has(dog.id)}
                  />
                  {uploadingIds.has(dog.id) && <small>Téléchargement...</small>}
                </label>

                <LoadingButton
                  className="danger"
                  onClick={() => removeDog(dog.id)}
                  loading={deletingIds.has(dog.id)}
                  loadingText="Suppression..."
                >
                  Supprimer
                </LoadingButton>

                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input
                    aria-label="ID co-propriétaire"
                    placeholder="ID utilisateur (8 chiffres)"
                    value={coOwnerUserId}
                    onChange={e => setCoOwnerUserId(e.target.value)}
                    style={{ width: 180 }}
                  />
                  <button onClick={() => addCoOwner(dog.id)}>Ajouter co-propriétaire</button>
                  <button onClick={() => removeCoOwner(dog.id)}>Retirer co-propriétaire</button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <hr style={{ margin: '32px 0', border: 'none', borderTop: '1px solid #ddd' }} />

        <h2>Rechercher des chiens</h2>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3>Filtres de recherche</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label>
                Nom du chien
                <input
                  placeholder="Recherche partielle..."
                  value={searchName}
                  onChange={e => setSearchName(e.target.value)}
                  disabled={searchLoading}
                  style={{ marginLeft: 8, width: 250 }}
                />
              </label>
            </div>

            {userLocation ? (
              <div>
                <label>
                  Rayon de recherche: {searchRadiusKm} km
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={searchRadiusKm}
                    onChange={e => setSearchRadiusKm(parseInt(e.target.value))}
                    disabled={searchLoading}
                    style={{ marginLeft: 8, width: 200 }}
                  />
                </label>
                <small style={{ display: 'block', marginTop: 4, color: '#666' }}>
                  Recherche autour de votre position
                </small>
              </div>
            ) : (
              <p style={{ color: '#666', fontSize: '0.9em' }}>
                💡 Définissez votre position dans votre profil pour activer la recherche par proximité
              </p>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              <LoadingButton
                onClick={() => { setSearchPage(1); searchDogs(); }}
                loading={searchLoading}
                loadingText="Recherche..."
              >
                Rechercher
              </LoadingButton>
              {hasSearched && (
                <button onClick={resetSearch} disabled={searchLoading}>
                  Réinitialiser
                </button>
              )}
            </div>
          </div>
        </div>

        {searchError && <p style={{ color: 'red' }}>{searchError}</p>}

        {searchLoading ? (
          <LoadingSpinner text="Recherche en cours..." />
        ) : hasSearched && searchResults.length === 0 ? (
          <p style={{ color: '#666', textAlign: 'center', padding: '24px 0' }}>
            Aucun chien trouvé avec ces critères
          </p>
        ) : hasSearched ? (
          <>
            <p style={{ marginBottom: 12, color: '#666' }}>
              {searchTotal} chien{searchTotal !== 1 ? 's' : ''} trouvé{searchTotal !== 1 ? 's' : ''}
            </p>
            <div className="list">
              {searchResults.map(dog => (
                <div key={dog.id} className="list-item">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    {dog.photo_url ? (
                      <img src={dog.photo_url} alt={dog.name} style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6 }} />
                    ) : (
                      <div style={{ width: 64, height: 64, background: '#eee', display: 'inline-block', borderRadius: 6 }} />
                    )}
                    <div style={{ flex: 1 }}>
                      <strong>{dog.name}</strong>
                      <div style={{ fontSize: '0.9em', color: '#666', marginTop: 4 }}>
                        {dog.sex === 'male' ? '♂ Mâle' : '♀ Femelle'} • {dog.age_years} {dog.age_years === 1 ? 'an' : 'ans'}
                      </div>
                      {dog.owner_name && (
                        <div style={{ fontSize: '0.85em', color: '#999', marginTop: 2 }}>
                          Propriétaire: {dog.owner_name}
                        </div>
                      )}
                      {dog.distance_km !== undefined && (
                        <div style={{ fontSize: '0.85em', color: '#999', marginTop: 2 }}>
                          📍 {dog.distance_km.toFixed(1)} km
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {searchTotal > 20 && (
              <div className="pager" style={{ marginTop: 16 }}>
                <button
                  onClick={() => setSearchPage(p => Math.max(1, p - 1))}
                  disabled={searchPage === 1 || searchLoading}
                >
                  Précédent
                </button>
                <span>Page {searchPage} / {Math.ceil(searchTotal / 20)}</span>
                <button
                  onClick={() => setSearchPage(p => p + 1)}
                  disabled={searchPage >= Math.ceil(searchTotal / 20) || searchLoading}
                >
                  Suivant
                </button>
              </div>
            )}
          </>
        ) : null}
    </div>
  )
}

export default Dogs
