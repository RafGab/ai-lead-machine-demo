import json

from backend.database.database import get_connection, _ensure_column


def create_tables() -> None:
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vertical TEXT NOT NULL,
            lead_data TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migración segura para bases de datos creadas antes de añadir "status".
    _ensure_column(connection, "demo_conversations", "status", "TEXT NOT NULL DEFAULT 'active'")
    # "source" distingue conversaciones iniciadas probando la demo
    # ("demo") de las de un widget embebido en la web real de un
    # cliente ("widget"), para no mezclar sus métricas.
    _ensure_column(connection, "demo_conversations", "source", "TEXT NOT NULL DEFAULT 'demo'")
    # Seguimiento del lead por parte del negocio (panel de leads).
    _ensure_column(connection, "demo_conversations", "lead_status", "TEXT NOT NULL DEFAULT 'nuevo'")
    _ensure_column(connection, "demo_conversations", "lead_note", "TEXT")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES demo_conversations(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            vertical TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            lead_name TEXT,
            lead_phone TEXT,
            lead_email TEXT,
            calendar_status TEXT NOT NULL DEFAULT 'pending',
            calendar_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES demo_conversations(id)
        )
    """)

    # Solicitudes de "hablar con una persona". Tabla propia (sin clave foránea)
    # porque la conversación puede ser de un rubro demo o de inmobiliaria, que
    # guarda las suyas en las tablas de producción.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vertical TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'demo',
            conversation_id INTEGER,
            name TEXT,
            contact TEXT NOT NULL,
            contact_type TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _ensure_column(connection, "demo_handoffs", "lead_status", "TEXT NOT NULL DEFAULT 'nuevo'")
    _ensure_column(connection, "demo_handoffs", "lead_note", "TEXT")

    connection.commit()
    connection.close()


def create_handoff(
    vertical: str,
    source: str,
    conversation_id: int | None,
    name: str | None,
    contact: str,
    contact_type: str,
    note: str | None,
) -> int:
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO demo_handoffs
        (vertical, source, conversation_id, name, contact, contact_type, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (vertical, source, conversation_id, name, contact, contact_type, note),
    )

    handoff_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return handoff_id


def recent_handoff_exists(vertical: str, contact: str, minutes: int = 10) -> bool:
    connection = get_connection()

    row = connection.execute(
        """
        SELECT 1 FROM demo_handoffs
        WHERE vertical = ? AND contact = ?
        AND created_at >= datetime('now', ?)
        LIMIT 1
        """,
        (vertical, contact, f"-{int(minutes)} minutes"),
    ).fetchone()

    connection.close()

    return row is not None


def count_handoffs(vertical: str) -> tuple[int, int]:
    """Devuelve (total, los pedidos desde la web real de un cliente)."""

    connection = get_connection()

    row = connection.execute(
        """
        SELECT COUNT(*) AS total,
               COALESCE(SUM(CASE WHEN source = 'widget' THEN 1 ELSE 0 END), 0) AS from_site
        FROM demo_handoffs WHERE vertical = ?
        """,
        (vertical,),
    ).fetchone()

    connection.close()

    return row["total"], row["from_site"]


def create_conversation(vertical: str, source: str = "demo") -> int:
    connection = get_connection()

    cursor = connection.execute(
        "INSERT INTO demo_conversations (vertical, lead_data, source) VALUES (?, ?, ?)",
        (vertical, "{}", source),
    )

    conversation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return conversation_id


def save_message(conversation_id: int, role: str, content: str) -> None:
    connection = get_connection()

    connection.execute(
        "INSERT INTO demo_messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )

    connection.execute(
        "UPDATE demo_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,),
    )

    connection.commit()
    connection.close()


def get_conversation(conversation_id: int) -> dict | None:
    connection = get_connection()

    conversation = connection.execute(
        "SELECT * FROM demo_conversations WHERE id = ?", (conversation_id,)
    ).fetchone()

    if conversation is None:
        connection.close()
        return None

    messages = connection.execute(
        "SELECT * FROM demo_messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()

    connection.close()

    return {
        "id": conversation["id"],
        "vertical": conversation["vertical"],
        "lead_data": json.loads(conversation["lead_data"]),
        "status": conversation["status"],
        "source": conversation["source"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
        "messages": [dict(message) for message in messages],
    }


def update_lead_data(conversation_id: int, lead_data: dict) -> None:
    connection = get_connection()

    connection.execute(
        "UPDATE demo_conversations SET lead_data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(lead_data, ensure_ascii=False), conversation_id),
    )

    connection.commit()
    connection.close()


def mark_completed(conversation_id: int) -> None:
    connection = get_connection()

    connection.execute(
        "UPDATE demo_conversations SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,),
    )

    connection.commit()
    connection.close()


def create_appointment(
    conversation_id: int,
    vertical: str,
    scheduled_at: str,
    lead_name: str | None = None,
    lead_phone: str | None = None,
    lead_email: str | None = None,
) -> int:
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO demo_appointments (
            conversation_id, vertical, scheduled_at, lead_name, lead_phone, lead_email
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, vertical, scheduled_at, lead_name, lead_phone, lead_email),
    )

    appointment_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return appointment_id


def set_appointment_calendar_result(
    appointment_id: int,
    calendar_status: str,
    calendar_event_id: str | None = None,
) -> None:
    connection = get_connection()

    connection.execute(
        "UPDATE demo_appointments SET calendar_status = ?, calendar_event_id = ? WHERE id = ?",
        (calendar_status, calendar_event_id, appointment_id),
    )

    connection.commit()
    connection.close()
