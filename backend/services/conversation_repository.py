import json

from backend.database.database import get_connection


def create_conversation() -> int:
    """
    Crea una nueva conversación y devuelve su ID.
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO conversations (lead_data)
        VALUES (?)
        """,
        ("{}",)
    )

    conversation_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return conversation_id


def save_message(
    conversation_id: int,
    role: str,
    content: str
) -> None:
    """
    Guarda un mensaje dentro de una conversación.
    """

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO messages (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content
        )
    )

    connection.execute(
        """
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()


def get_conversation(conversation_id: int) -> dict | None:
    """
    Recupera una conversación por su ID.
    """

    connection = get_connection()

    conversation = connection.execute(
        """
        SELECT *
        FROM conversations
        WHERE id = ?
        """,
        (conversation_id,)
    ).fetchone()

    if conversation is None:
        connection.close()
        return None

    messages = connection.execute(
        """
        SELECT *
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    ).fetchall()

    connection.close()

    return {
        "id": conversation["id"],
        "lead_data": json.loads(conversation["lead_data"]),
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
        "messages": [dict(message) for message in messages]
    }


def list_conversations() -> list[dict]:
    """
    Devuelve un resumen de todas las conversaciones (para el listado
    de leads), con el último mensaje y ordenadas por actividad
    reciente.
    """

    connection = get_connection()

    conversations = connection.execute(
        """
        SELECT *
        FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()

    summaries = []

    for conversation in conversations:
        last_message = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (conversation["id"],)
        ).fetchone()

        summaries.append({
            "id": conversation["id"],
            "lead_data": json.loads(conversation["lead_data"]),
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "last_message": dict(last_message) if last_message else None,
        })

    connection.close()

    return summaries


def update_lead_data(
    conversation_id: int,
    lead_data: dict
) -> None:
    """
    Actualiza los datos estructurados del lead
    asociados a una conversación.
    """

    connection = get_connection()

    connection.execute(
        """
        UPDATE conversations
        SET lead_data = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            json.dumps(lead_data, ensure_ascii=False),
            conversation_id
        )
    )

    connection.commit()
    connection.close()