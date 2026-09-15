import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('')
  const [properties, setProperties] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [lead, setLead] = useState({})
  const [visitFormPropertyId, setVisitFormPropertyId] = useState(null)
  const [visitForm, setVisitForm] = useState({
    date: '',
    time: '',
    name: '',
    phone: '',
    email: ''
  })
  const [visitStatusByProperty, setVisitStatusByProperty] = useState({})
  const [conversations, setConversations] = useState([])
  const WELCOME_MESSAGE = {
    role: 'assistant',
    content:
      'Hola 👋 Soy tu agente de atención. Puedo ayudarte a encontrar la propiedad que necesitas.'
  }
  const [messages, setMessages] = useState([WELCOME_MESSAGE])

  const getInitials = (name) => {
    if (!name) return '?'

    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('')
  }

  const formatConversationTime = (dateString) => {
    if (!dateString) return ''

    const date = new Date(dateString.replace(' ', 'T') + 'Z')
    if (Number.isNaN(date.getTime())) return ''

    const now = new Date()
    const sameDay = date.toDateString() === now.toDateString()

    if (sameDay) {
      return date.toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit'
    })
  }

  const loadConversations = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/conversations')

      if (!response.ok) {
        throw new Error('No se pudieron cargar las conversaciones')
      }

      const data = await response.json()

      setConversations(data)
    } catch (error) {
      console.error(error)
    }
  }

  useEffect(() => {
    loadConversations()
  }, [])

  const selectConversation = async (id) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/conversations/${id}`)

      if (!response.ok) {
        throw new Error('No se pudo cargar la conversación')
      }

      const data = await response.json()

      setConversationId(data.id)
      setLead(data.lead_data || {})
      setMessages(
        data.messages.length > 0
          ? data.messages.map((item) => ({
              role: item.role,
              content: item.content
            }))
          : [WELCOME_MESSAGE]
      )
      setVisitFormPropertyId(null)
    } catch (error) {
      console.error(error)
    }
  }

  const startNewConversation = () => {
    setConversationId(null)
    setLead({})
    setMessages([WELCOME_MESSAGE])
    setVisitFormPropertyId(null)
  }

    const loadProperties = async () => {
    try {
      const response = await fetch(
        'http://127.0.0.1:8000/properties'
      )

      if (!response.ok) {
        throw new Error('No se pudieron cargar las propiedades')
      }

      const data = await response.json()

      setProperties(data)
    } catch (error) {
      console.error(error)
    }
  }

  const searchProperties = async (criteria) => {
  try {
    const response = await fetch(
      'http://127.0.0.1:8000/search',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(criteria)
      }
    )

    if (!response.ok) {
      throw new Error('No se pudieron buscar propiedades')
    }

    const data = await response.json()

    setProperties(data.results)
  } catch (error) {
    console.error(error)
  }
}

  useEffect(() => {
  if (!lead.city && !lead.property_type && !lead.max_price) {
    loadProperties()
    return
  }

  searchProperties({
    city: lead.city || undefined,
    operation: lead.operation || undefined,
    property_type: lead.property_type || undefined,
    max_price: lead.max_price || undefined,
    bedrooms: lead.bedrooms || undefined
  })
}, [
  lead.city,
  lead.operation,
  lead.property_type,
  lead.max_price,
  lead.bedrooms
])

  const sendMessage = async () => {
    if (!message.trim()) return

    const userMessage = message

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: 'user',
        content: userMessage
      }
    ])

    setMessage('')

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/conversations/message',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMessage,
            conversation_id: conversationId
          })
        }
      )

      if (!response.ok) {
        throw new Error('Error al comunicarse con el servidor')
      }

      const data = await response.json()

      setConversationId(data.conversation_id)
      setLead(data.lead)

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          content: data.assistant_message
        }
      ])

      loadConversations()
    } catch (error) {
      console.error(error)

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          content:
            'Lo siento, ha ocurrido un problema al conectar con el agente.'
        }
      ])
    }
  }
  const openVisitForm = (propertyId) => {
    setVisitFormPropertyId(propertyId)
    setVisitForm({
      date: '',
      time: '',
      name: lead.name || '',
      phone: lead.phone || '',
      email: lead.email || ''
    })
  }

  const submitVisit = async (propertyId) => {
    if (!visitForm.date || !visitForm.time) {
      setVisitStatusByProperty((current) => ({
        ...current,
        [propertyId]: 'Indica fecha y hora para la visita.'
      }))
      return
    }

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/visits',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            property_id: propertyId,
            scheduled_at: `${visitForm.date}T${visitForm.time}:00`,
            conversation_id: conversationId,
            lead_name: visitForm.name || null,
            lead_phone: visitForm.phone || null,
            lead_email: visitForm.email || null
          })
        }
      )

      if (!response.ok) {
        throw new Error('No se pudo agendar la visita')
      }

      const data = await response.json()

      setVisitStatusByProperty((current) => ({
        ...current,
        [propertyId]: data.message
      }))

      setVisitFormPropertyId(null)
    } catch (error) {
      console.error(error)

      setVisitStatusByProperty((current) => ({
        ...current,
        [propertyId]: 'No se pudo agendar la visita. Inténtalo de nuevo.'
      }))
    }
  }

  return (
    <div className="app">

      {/* BARRA SUPERIOR */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <strong>Agente IA</strong>
            <span>Intelligent Lead Management</span>
          </div>
        </div>

        <div className="agent-status">
          <span className="status-dot"></span>
          Agente activo
        </div>
      </header>


      {/* CONTENIDO PRINCIPAL */}
      <main className="dashboard">

        {/* CONVERSACIONES */}
        <aside className="conversations">
          <div className="panel-title">
            <h2>Conversaciones</h2>
            <span>{conversations.length}</span>
          </div>

          <div
            className={`conversation ${conversationId === null ? 'active' : ''}`}
            onClick={startNewConversation}
          >
            <div className="avatar">+</div>

            <div className="conversation-info">
              <strong>Nueva conversación</strong>
              <p>Empezar de cero</p>
            </div>
          </div>

          {conversations.map((conversation) => {
            const name = conversation.lead_data?.name

            return (
              <div
                key={conversation.id}
                className={`conversation ${conversation.id === conversationId ? 'active' : ''}`}
                onClick={() => selectConversation(conversation.id)}
              >
                <div className="avatar">{getInitials(name)}</div>

                <div className="conversation-info">
                  <strong>{name || `Lead #${conversation.id}`}</strong>
                  <p>{conversation.last_message?.content || 'Sin mensajes'}</p>
                </div>

                <small>{formatConversationTime(conversation.updated_at)}</small>
              </div>
            )
          })}
        </aside>


        {/* CHAT */}
        <section className="chat">

          <div className="chat-header">
            <div>
              <h2>{lead.name || (conversationId ? `Lead #${conversationId}` : 'Nueva conversación')}</h2>
              <p>Conversación con agente IA</p>
            </div>

            <span className="lead-badge">
              Lead activo
            </span>
          </div>


          <div className="messages">

            {messages.map((item, index) => (
              <div
                key={index}
                className={`message ${item.role}`}
              >
                <div className="message-bubble">
                  {item.content}
                </div>
              </div>
            ))}

          </div>


          <div className="message-input">

            <input
              type="text"
              placeholder="Escribe un mensaje..."
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  sendMessage()
                }
              }}
            />

            <button onClick={sendMessage}>
              Enviar
            </button>

          </div>

        </section>

                {/* PROPIEDADES */}
        <section className="properties-panel">

          <div className="properties-header">
            <h2>Propiedades disponibles</h2>
            <span>{properties.length}</span>
          </div>

          <div className="properties-grid">

            {properties.map((property) => (

              <article
                className="property-card"
                key={property.id}
              >

                {property.images?.length > 0 && (
                  <img
                    src={`http://127.0.0.1:8000${property.images[0]}`}
                    alt={property.title}
                    className="property-image"
                  />
                )}

                <div className="property-content">

                  <h3>{property.title}</h3>

                  <p>
                    {property.city}
                  </p>

                  <strong>
                    {property.operation === 'venta'
  ? `${property.price.toLocaleString('es-ES')} €`
  : `${property.price.toLocaleString('es-ES')} €/mes`}
                  </strong>

                  {property.bedrooms && (
                    <span>
                      🛏️ {property.bedrooms} habitación
                      {property.bedrooms > 1 ? 'es' : ''}
                    </span>
                  )}

                  {visitFormPropertyId === property.id ? (
                    <div className="visit-form">
                      <div className="visit-form-row">
                        <input
                          type="date"
                          value={visitForm.date}
                          onChange={(event) =>
                            setVisitForm((current) => ({
                              ...current,
                              date: event.target.value
                            }))
                          }
                        />
                        <input
                          type="time"
                          value={visitForm.time}
                          onChange={(event) =>
                            setVisitForm((current) => ({
                              ...current,
                              time: event.target.value
                            }))
                          }
                        />
                      </div>

                      <input
                        type="text"
                        placeholder="Nombre"
                        value={visitForm.name}
                        onChange={(event) =>
                          setVisitForm((current) => ({
                            ...current,
                            name: event.target.value
                          }))
                        }
                      />

                      <input
                        type="tel"
                        placeholder="Teléfono"
                        value={visitForm.phone}
                        onChange={(event) =>
                          setVisitForm((current) => ({
                            ...current,
                            phone: event.target.value
                          }))
                        }
                      />

                      <input
                        type="email"
                        placeholder="Email"
                        value={visitForm.email}
                        onChange={(event) =>
                          setVisitForm((current) => ({
                            ...current,
                            email: event.target.value
                          }))
                        }
                      />

                      <div className="visit-form-actions">
                        <button
                          type="button"
                          className="visit-cancel"
                          onClick={() => setVisitFormPropertyId(null)}
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          className="visit-confirm"
                          onClick={() => submitVisit(property.id)}
                        >
                          Confirmar visita
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="schedule-visit-button"
                      onClick={() => openVisitForm(property.id)}
                    >
                      📅 Agendar visita
                    </button>
                  )}

                  {visitStatusByProperty[property.id] && (
                    <p className="visit-status">
                      {visitStatusByProperty[property.id]}
                    </p>
                  )}

                </div>

              </article>

            ))}

          </div>

        </section>


        {/* INFORMACIÓN DEL LEAD */}
        <aside className="lead-panel">

          <div className="lead-header">
            <h2>Información del lead</h2>
            <span className="qualified">Activo</span>
          </div>


          <div className="lead-section">
            <span className="label">Operación</span>
            <strong>{lead.operation || '—'}</strong>
          </div>

          <div className="lead-section">
            <span className="label">Tipo de inmueble</span>
            <strong>{lead.property_type || '—'}</strong>
          </div>

          <div className="lead-section">
            <span className="label">Ciudad</span>
            <strong>{lead.city || '—'}</strong>
          </div>

            <div className="lead-section">
              <span className="label">Presupuesto máximo</span>
              <strong>
            {lead.max_price ? `${lead.max_price} €/mes` : '—'}
              </strong>
            </div>

          <div className="lead-section">
            <span className="label">Entrada</span>
            <strong>{lead.move_in_date || '—'}</strong>
          </div>

          <div className="lead-section">
            <span className="label">Personas</span>
            <strong>{lead.occupants ?? '—'}</strong>
          </div>

          <div className="lead-section">
            <span className="label">Mascotas</span>
            <strong>
                   {lead.has_pets === true
                    ? 'Sí 🐕'
                  : lead.has_pets === false
                  ? 'No'
              : '—'}
           </strong>
          </div>


          <div className="lead-footer">
            <span>Estado del lead</span>
            <strong>🟢 En proceso</strong>
          </div>

        </aside>

      </main>

    </div>
  )
}

export default App