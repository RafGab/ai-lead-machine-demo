from backend.database.database import get_connection


def create_visit(
    property_id: int,
    scheduled_at: str,
    conversation_id: int | None = None,
    lead_name: str | None = None,
    lead_phone: str | None = None,
    lead_email: str | None = None,
) -> int:
    """
    Crea una visita y devuelve su ID.
    """

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO visits (
            conversation_id,
            property_id,
            scheduled_at,
            lead_name,
            lead_phone,
            lead_email
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            property_id,
            scheduled_at,
            lead_name,
            lead_phone,
            lead_email,
        ),
    )

    visit_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return visit_id


def set_visit_calendar_result(
    visit_id: int,
    calendar_status: str,
    calendar_event_id: str | None = None,
) -> None:
    """
    Actualiza el resultado de la sincronización con el calendario.
    """

    connection = get_connection()

    connection.execute(
        """
        UPDATE visits
        SET calendar_status = ?,
            calendar_event_id = ?
        WHERE id = ?
        """,
        (calendar_status, calendar_event_id, visit_id),
    )

    connection.commit()
    connection.close()


def get_visit(visit_id: int) -> dict | None:
    connection = get_connection()

    row = connection.execute(
        "SELECT * FROM visits WHERE id = ?",
        (visit_id,),
    ).fetchone()

    connection.close()

    return dict(row) if row else None


def list_visits() -> list[dict]:
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            visits.*,
            properties.title AS property_title
        FROM visits
        JOIN properties ON properties.id = visits.property_id
        ORDER BY visits.scheduled_at ASC
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]
