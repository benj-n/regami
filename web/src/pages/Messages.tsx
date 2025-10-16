import React, { useEffect, useState } from 'react'
import { apiGet, apiPost } from '../services/api'
import { useToast } from '../context/ToastContext'
import { useWebSocket } from '../context/WebSocketContext'
import LoadingSpinner from '../components/LoadingSpinner'
import LoadingButton from '../components/LoadingButton'

type ConversationSummary = {
  other_user_id: string
  other_user_email: string
  last_message: string
  last_message_at: string
  unread_count: number
}

type Message = {
  id: number
  sender_id: string
  recipient_id: string
  content: string
  is_read: boolean
  created_at: string
  sender_email?: string
  recipient_email?: string
}

const Messages: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const { push } = useToast()
  const { lastMessage } = useWebSocket()

  // Load conversations list
  async function loadConversations() {
    try {
      setLoading(true)
      setError('')
      const data = await apiGet<ConversationSummary[]>('/messages/conversations')
      setConversations(data)
    } catch (e: any) {
      setError(e.message || 'Erreur lors du chargement des conversations')
    } finally {
      setLoading(false)
    }
  }

  // Load messages for a specific conversation
  async function loadMessages(userId: string) {
    try {
      setLoadingMessages(true)
      const data = await apiGet<Message[]>(`/messages/conversations/${userId}`)
      // Reverse to show oldest first (chronological order)
      setMessages(data.reverse())
    } catch (e: any) {
      push(e.message || 'Erreur lors du chargement des messages', { type: 'error' })
    } finally {
      setLoadingMessages(false)
    }
  }

  // Send a new message
  async function handleSendMessage() {
    if (!selectedUserId || !newMessage.trim()) return

    try {
      setSending(true)
      const message = await apiPost<Message>('/messages', {
        recipient_id: selectedUserId,
        content: newMessage.trim(),
      })

      // Add the new message to the thread
      setMessages(prev => [...prev, message])
      setNewMessage('')

      // Reload conversations to update last message
      loadConversations()

      push('Message envoyé', { type: 'success' })
    } catch (e: any) {
      push(e.message || 'Erreur lors de l\'envoi', { type: 'error' })
    } finally {
      setSending(false)
    }
  }

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [])

  // Listen for new messages via WebSocket
  useEffect(() => {
    if (lastMessage?.type === 'new_message') {
      // Reload conversations to update unread counts
      void loadConversations()

      // If we're viewing the conversation with the sender, reload messages
      if (selectedUserId && selectedUserId === lastMessage.data.sender_id) {
        void loadMessages(selectedUserId)
      }
    }
  }, [lastMessage, selectedUserId])

  // Load messages when selecting a conversation
  useEffect(() => {
    if (selectedUserId) {
      void loadMessages(selectedUserId)
    }
  }, [selectedUserId])

  const selectedConversation = conversations.find(c => c.other_user_id === selectedUserId)

  return (
    <div className="container">
      <h1>💬 Messages</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1rem', marginTop: '1rem', minHeight: '500px' }}>
        {/* Conversations List */}
        <div style={{ borderRight: '1px solid #ddd', paddingRight: '1rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Conversations</h2>
          {loading ? (
            <LoadingSpinner />
          ) : conversations.length === 0 ? (
            <p style={{ color: '#666', fontStyle: 'italic' }}>Aucune conversation</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {conversations.map((conv) => (
                <div
                  key={conv.other_user_id}
                  onClick={() => setSelectedUserId(conv.other_user_id)}
                  style={{
                    padding: '1rem',
                    border: selectedUserId === conv.other_user_id ? '2px solid #667eea' : '1px solid #ddd',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    backgroundColor: selectedUserId === conv.other_user_id ? '#f0f4ff' : 'white',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedUserId !== conv.other_user_id) {
                      e.currentTarget.style.backgroundColor = '#f9fafb'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedUserId !== conv.other_user_id) {
                      e.currentTarget.style.backgroundColor = 'white'
                    }
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <strong style={{ fontSize: '1rem' }}>{conv.other_user_email}</strong>
                    {conv.unread_count > 0 && (
                      <span
                        style={{
                          backgroundColor: '#ef4444',
                          color: 'white',
                          borderRadius: '12px',
                          padding: '2px 8px',
                          fontSize: '0.75rem',
                          fontWeight: 'bold',
                        }}
                      >
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: '0.875rem', color: '#666', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {conv.last_message}
                  </p>
                  <p style={{ fontSize: '0.75rem', color: '#999', margin: '0.25rem 0 0 0' }}>
                    {new Date(conv.last_message_at).toLocaleString('fr-FR', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Message Thread */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '500px' }}>
          {!selectedUserId ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
              <p>Sélectionnez une conversation pour voir les messages</p>
            </div>
          ) : (
            <>
              {/* Thread Header */}
              <div style={{ borderBottom: '1px solid #ddd', paddingBottom: '1rem', marginBottom: '1rem' }}>
                <h2 style={{ fontSize: '1.2rem', margin: 0 }}>
                  Conversation avec {selectedConversation?.other_user_email}
                </h2>
              </div>

              {/* Messages */}
              <div style={{ flex: 1, overflowY: 'auto', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {loadingMessages ? (
                  <LoadingSpinner />
                ) : messages.length === 0 ? (
                  <p style={{ color: '#666', fontStyle: 'italic' }}>Aucun message dans cette conversation</p>
                ) : (
                  messages.map((msg) => {
                    const isSent = msg.sender_id !== selectedUserId
                    return (
                      <div
                        key={msg.id}
                        style={{
                          alignSelf: isSent ? 'flex-end' : 'flex-start',
                          maxWidth: '70%',
                        }}
                      >
                        <div
                          style={{
                            padding: '0.75rem',
                            borderRadius: '12px',
                            backgroundColor: isSent ? '#667eea' : '#f3f4f6',
                            color: isSent ? 'white' : 'black',
                          }}
                        >
                          <p style={{ margin: 0, wordWrap: 'break-word' }}>{msg.content}</p>
                        </div>
                        <p
                          style={{
                            fontSize: '0.75rem',
                            color: '#999',
                            margin: '0.25rem 0.5rem 0',
                            textAlign: isSent ? 'right' : 'left',
                          }}
                        >
                          {new Date(msg.created_at).toLocaleString('fr-FR', {
                            day: '2-digit',
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Message Composer */}
              <div style={{ borderTop: '1px solid #ddd', paddingTop: '1rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Écrivez votre message..."
                    rows={3}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '8px',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                  />
                  <LoadingButton
                    onClick={handleSendMessage}
                    loading={sending}
                    loadingText="Envoi..."
                    disabled={!newMessage.trim()}
                    style={{ alignSelf: 'flex-end' }}
                  >
                    Envoyer
                  </LoadingButton>
                </div>
                <p style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.5rem' }}>
                  {newMessage.length}/5000 caractères • Appuyez sur Entrée pour envoyer
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default Messages
