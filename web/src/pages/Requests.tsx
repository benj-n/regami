import React, { useEffect, useState } from 'react'
import { apiDeleteVoid, apiGet, apiPost } from '../services/api'
import { useToast } from '../context/ToastContext'
import LoadingSpinner from '../components/LoadingSpinner'
import LoadingButton from '../components/LoadingButton'
import DateTimePicker from '../components/DateTimePicker'

// Helper to convert Date to ISO string
const toIsoString = (date: Date | null): string => {
  if (!date) return ''
  return date.toISOString()
}

const Requests: React.FC = () => {
  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)
  const [info, setInfo] = useState('')
  const [mine, setMine] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [sort, setSort] = useState('-start_at')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set())
  const [error, setError] = useState('')
  const { push } = useToast()

  // Search state
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchStartDate, setSearchStartDate] = useState<Date | null>(null)
  const [searchEndDate, setSearchEndDate] = useState<Date | null>(null)
  const [excludeMine, setExcludeMine] = useState(true)
  const [searchSort, setSearchSort] = useState('-start_at')
  const [searchPage, setSearchPage] = useState(1)
  const [searchPageSize] = useState(20)
  const [searchTotal, setSearchTotal] = useState(0)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  async function submit() {
    if (!startDate || !endDate) {
      push('Veuillez sélectionner les dates de début et de fin', { type: 'error' })
      return
    }
    if (startDate >= endDate) {
      push('La date de fin doit être après la date de début', { type: 'error' })
      return
    }
    try {
      setInfo('')
      setSubmitting(true)
      await apiPost('/availability/requests', {
        start_at: toIsoString(startDate),
        end_at: toIsoString(endDate)
      })
      push('Demande créée', { type: 'success' })
      setStartDate(null)
      setEndDate(null)
      loadMine()
    } catch (e: any) {
      push(e.message || 'Erreur lors de la création', { type: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  async function loadMine() {
    try {
      setLoading(true)
      setError('')
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort })
      const data = await apiGet<{ items: any[]; total: number; page: number; page_size: number }>(`/availability/requests/mine?${params}`)
      setMine(data.items)
      setTotal(data.total)
    } catch (e: any) {
      setError(e.message || 'Erreur lors du chargement')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMine() }, [page, sort])

  async function searchRequests() {
    try {
      setSearchLoading(true)
      setSearchError('')
      setHasSearched(true)

      const params = new URLSearchParams({
        page: String(searchPage),
        page_size: String(searchPageSize),
        sort: searchSort,
        exclude_mine: String(excludeMine),
      })

      if (searchStartDate) {
        params.append('start_date', toIsoString(searchStartDate))
      }
      if (searchEndDate) {
        params.append('end_date', toIsoString(searchEndDate))
      }

      const data = await apiGet<{ items: any[]; total: number; page: number; page_size: number; has_more: boolean }>(
        `/availability/requests/search?${params}`
      )
      setSearchResults(data.items)
      setSearchTotal(data.total)
    } catch (e: any) {
      setSearchError(e.message || 'Erreur lors de la recherche')
    } finally {
      setSearchLoading(false)
    }
  }

  // Trigger search when page or sort changes
  useEffect(() => {
    if (hasSearched) {
      searchRequests()
    }
  }, [searchPage, searchSort])

  const resetSearch = () => {
    setSearchStartDate(null)
    setSearchEndDate(null)
    setExcludeMine(true)
    setSearchSort('-start_at')
    setSearchPage(1)
    setSearchResults([])
    setSearchTotal(0)
    setHasSearched(false)
    setSearchError('')
  }

  async function remove(id: number) {
    try {
      setDeletingIds(prev => new Set(prev).add(id))
      await apiDeleteVoid(`/availability/requests/${id}`)
      push('Demande supprimée', { type: 'success' })
      loadMine()
    } catch (e: any) {
      push(e.message || 'Erreur lors de la suppression', { type: 'error' })
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  return (
    <div className="container">
      <h1>Demandes</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 16 }}>
        <DateTimePicker
          id="req-start"
          label="Début"
          selected={startDate}
          onChange={setStartDate}
          disabled={submitting}
          minDate={new Date()}
          placeholderText="Sélectionner la date de début..."
        />

        <DateTimePicker
          id="req-end"
          label="Fin"
          selected={endDate}
          onChange={setEndDate}
          disabled={submitting}
          minDate={startDate || new Date()}
          placeholderText="Sélectionner la date de fin..."
        />
      </div>

      <LoadingButton
        onClick={submit}
        loading={submitting}
        loadingText="Publication..."
      >
        Publier une demande
      </LoadingButton>
      <h2>Mes demandes</h2>
      <div style={{ margin: '8px 0' }}>
        Tri:
        <select value={sort} onChange={e => setSort(e.target.value)} style={{ marginLeft: 8 }} disabled={loading}>
          <option value="-start_at">Début décroissant</option>
          <option value="start_at">Début croissant</option>
        </select>
      </div>
      {loading ? (
        <LoadingSpinner text="Chargement des demandes..." />
      ) : (
        <ul>
          {mine.map(o => (
            <li key={o.id} className="list-item">
              <span>{new Date(o.start_at).toLocaleString()} → {new Date(o.end_at).toLocaleString()}</span>
              <LoadingButton
                onClick={() => remove(o.id)}
                className="danger"
                loading={deletingIds.has(o.id)}
                loadingText="Suppression..."
              >
                Supprimer
              </LoadingButton>
            </li>
          ))}
        </ul>
      )}
      <div className="pager">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Précédent</button>
        <span>Page {page} / {Math.max(1, Math.ceil(total / pageSize))}</span>
        <button onClick={() => setPage(p => (p < Math.ceil(total / pageSize) ? p + 1 : p))} disabled={page >= Math.ceil(total / pageSize)}>Suivant</button>
      </div>

      <hr style={{ margin: '32px 0', border: 'none', borderTop: '1px solid #ddd' }} />

      <h2>Rechercher des demandes</h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Filtres de recherche</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16 }}>
            <DateTimePicker
              label="Date de début (après)"
              selected={searchStartDate}
              onChange={setSearchStartDate}
              disabled={searchLoading}
              placeholderText="Début de la période..."
            />

            <DateTimePicker
              label="Date de fin (avant)"
              selected={searchEndDate}
              onChange={setSearchEndDate}
              disabled={searchLoading}
              minDate={searchStartDate || undefined}
              placeholderText="Fin de la période..."
            />
          </div>

          <div>
            <label>
              <input
                type="checkbox"
                checked={excludeMine}
                onChange={e => setExcludeMine(e.target.checked)}
                disabled={searchLoading}
              />
              {' '}Exclure mes demandes
            </label>
          </div>

          <div>
            <label>
              Trier par:
              <select
                value={searchSort}
                onChange={e => setSearchSort(e.target.value)}
                style={{ marginLeft: 8 }}
                disabled={searchLoading}
              >
                <option value="-start_at">Début décroissant</option>
                <option value="start_at">Début croissant</option>
                <option value="-end_at">Fin décroissant</option>
                <option value="end_at">Fin croissant</option>
                <option value="-created_at">Plus récentes</option>
                <option value="created_at">Plus anciennes</option>
              </select>
            </label>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <LoadingButton
              onClick={() => { setSearchPage(1); searchRequests(); }}
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
          Aucune demande trouvée avec ces critères
        </p>
      ) : hasSearched ? (
        <>
          <p style={{ marginBottom: 12, color: '#666' }}>
            {searchTotal} demande{searchTotal !== 1 ? 's' : ''} trouvée{searchTotal !== 1 ? 's' : ''}
          </p>
          <ul>
            {searchResults.map(r => (
              <li key={r.id} className="list-item">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div>
                    <strong>{new Date(r.start_at).toLocaleString()} → {new Date(r.end_at).toLocaleString()}</strong>
                  </div>
                  {r.user_email && (
                    <div style={{ fontSize: '0.85em', color: '#666' }}>
                      Contact: {r.user_email}
                    </div>
                  )}
                  <div style={{ fontSize: '0.8em', color: '#999' }}>
                    Créée le {new Date(r.created_at).toLocaleDateString()}
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {searchTotal > searchPageSize && (
            <div className="pager" style={{ marginTop: 16 }}>
              <button
                onClick={() => setSearchPage(p => Math.max(1, p - 1))}
                disabled={searchPage === 1 || searchLoading}
              >
                Précédent
              </button>
              <span>Page {searchPage} / {Math.ceil(searchTotal / searchPageSize)}</span>
              <button
                onClick={() => setSearchPage(p => p + 1)}
                disabled={searchPage >= Math.ceil(searchTotal / searchPageSize) || searchLoading}
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

export default Requests
