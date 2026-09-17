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

    connection.commit()
    connection.close()


def create_conversation(vertical: str) -> int:
    connection = get_connection()

    cursor = connection.execute(
        "INSERT INTO demo_conversations (vertical, lead_data) VALUES (?, ?)",
        (vertical, "{}"),
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
