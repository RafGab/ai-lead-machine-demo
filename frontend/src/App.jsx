import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('')
  const [properties, setProperties] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [lead, setLead] = useState({})
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hola 👋 Soy tu agente de atención. Puedo ayudarte a encontrar la propiedad que necesitas.'
    }
  ])

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
    property_type: lead.property_type || undefined,
    max_price: lead.max_price || undefined,
    bedrooms: lead.bedrooms || undefined
  })
}, [
  lead.city,
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
            <span>3</span>
          </div>

          <div className="conversation active">
            <div className="avatar">CL</div>

            <div className="conversation-info">
              <strong>Cliente #001</strong>
              <p>Busco un piso en León...</p>
            </div>

            <small>Ahora</small>
          </div>

          <div className="conversation">
            <div className="avatar">MR</div>

            <div className="conversation-info">
              <strong>Cliente #002</strong>
              <p>Quería información sobre...</p>
            </div>

            <small>10:42</small>
          </div>

          <div className="conversation">
            <div className="avatar">AP</div>

            <div className="conversation-info">
              <strong>Cliente #003</strong>
              <p>¿Aceptan mascotas?</p>
            </div>

            <small>Ayer</small>
          </div>
        </aside>


        {/* CHAT */}
        <section className="chat">

          <div className="chat-header">
            <div>
              <h2>Cliente #001</h2>
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