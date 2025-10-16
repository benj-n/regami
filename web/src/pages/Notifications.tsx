import React, { useEffect, useState } from 'react'
import { apiGet, apiPostVoid, apiPutVoid } from '../services/api'
import { useToast } from '../context/ToastContext'
import LoadingSpinner from '../components/LoadingSpinner'
import LoadingButton from '../components/LoadingButton'

const Notifications: React.FC = () => {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [markingAllRead, setMarkingAllRead] = useState(false)
  const [markingReadIds, setMarkingReadIds] = useState<Set<number>>(new Set())
  const [error, setError] = useState('')
  const { push } = useToast()

  async function loadNotifications() {
    try {
      setLoading(true)
      setError('')
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), unread_only: String(unreadOnly) })
      const data = await apiGet<{ items: any[]; total: number }>(`/notifications/me?${params}`)
      setItems(data.items)
      setTotal(data.total)
    } catch (e: any) {
      setError(e.message || 'Erreur lors du chargement')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()
  }, [page, unreadOnly])

  async function markRead(id: number) {
    try {
      setMarkingReadIds(prev => new Set(prev).add(id))
      await apiPutVoid(`/notifications/${id}/read`)
      push('Notification lue', { type: 'success' })
      loadNotifications()
    } catch (e: any) {
      push(e.message || 'Erreur', { type: 'error' })
    } finally {
      setMarkingReadIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  async function markAll() {
    try {
      setMarkingAllRead(true)
      await apiPostVoid('/notifications/me/read-all')
      push('Toutes les notifications marquées comme lues', { type: 'success' })
      loadNotifications()
    } catch (e: any) {
      push(e.message || 'Erreur', { type: 'error' })
    } finally {
      setMarkingAllRead(false)
    }
  }

  return (
    <div className="container">
      <h1>Notifications</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
        <LoadingButton
          onClick={markAll}
          loading={markingAllRead}
          loadingText="Marquage..."
        >
          Tout marquer comme lu
        </LoadingButton>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={e => { setPage(1); setUnreadOnly(e.target.checked) }}
            disabled={loading}
          />
          Unread only
        </label>
      </div>
      {loading ? (
        <LoadingSpinner text="Chargement des notifications..." />
      ) : (
        <ul>
          {items.map(n => (
            <li key={n.id} className="list-item">
              <span>
                {n.message} — {new Date(n.created_at).toLocaleString()} {n.is_read ? '(lu)' : ''}
              </span>
              {!n.is_read && (
                <LoadingButton
                  onClick={() => markRead(n.id)}
                  loading={markingReadIds.has(n.id)}
                  loadingText="Marquage..."
                >
                  Marquer lu
                </LoadingButton>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="pager">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Précédent</button>
        <span>Page {page} / {Math.max(1, Math.ceil(total / pageSize))}</span>
        <button onClick={() => setPage(p => (p < Math.ceil(total / pageSize) ? p + 1 : p))} disabled={page >= Math.ceil(total / pageSize)}>Suivant</button>
      </div>
    </div>
  )
}

export default Notifications
