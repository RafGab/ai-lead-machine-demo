import csv
import io
import json
import re
from collections import defaultdict

from backend.database.database import get_connection
from backend.demo.field_labels import FIELD_LABELS, PII_FIELDS
from backend.demo.verticals import vertical_label
from backend.services import conversation_repository

STATUSES = ("nuevo", "contactado", "cerrado")
STATUS_RANK = {status: rank for rank, status in enumerate(STATUSES)}

TABLE_BY_KIND = {"c": "demo_conversations", "h": "demo_handoffs"}

CSV_COLUMNS = [
    "Fecha (UTC)", "Rubro", "Origen", "Estado", "Urgente", "Nombre",
    "Teléfono", "Correo", "Detalles", "Cita", "Nota",
]

PHONE_LIKE = re.compile(r"^[+\-]?[\d\s().\-]+$")


def _iso(timestamp: str | None) -> str | None:
    """SQLite guarda UTC como 'YYYY-MM-DD HH:MM:SS'; el panel lo convierte a hora local."""

    return timestamp.replace(" ", "T") + "Z" if timestamp else None


def _details(lead: dict) -> list[dict]:
    details = []

    for field, value in lead.items():
        if field in PII_FIELDS or value in (None, "", False):
            continue

        details.append({
            "label": FIELD_LABELS.get(field, field),
            "value": "sí" if value is True else str(value),
        })

    return details


def _row(
    lead_id: str, kind: str, vertical: str, source: str, created_at: str, updated_at: str | None,
    lead: dict, name, phone, email, status: str, note: str | None,
    completed: bool, handoffs: list[dict], appointment: dict | None,
) -> dict:
    return {
        "id": lead_id,
        "kind": kind,
        "vertical": vertical,
        "vertical_label": vertical_label(vertical),
        "source": source,
        "created_at": _iso(created_at),
        "updated_at": _iso(updated_at),
        "status": status if status in STATUSES else STATUSES[0],
        "note": note or "",
        "name": name or "",
        "phone": phone or "",
        "email": email or "",
        "details": _details(lead),
        "completed": completed,
        "urgent": bool(handoffs),
        "handoff_note": next((h["note"] for h in reversed(handoffs) if h["note"]), ""),
        "appointment": appointment,
    }


def list_leads(
    vertical: str | None = None,
    scope: str = "site",
    status: str | None = None,
    include_incomplete: bool = False,
) -> dict:
    """
    Leads de los rubros de la demo, uno por conversación, más las solicitudes
    de "hablar con una persona" que no cuelgan de ninguna. Por defecto solo
    los que llegan desde la web real de un cliente y se pueden contactar
    (tienen teléfono o correo).
    """

    connection = get_connection()

    conversations = connection.execute(
        "SELECT id, vertical, lead_data, status, source, created_at, updated_at, "
        "lead_status, lead_note FROM demo_conversations"
    ).fetchall()
    handoffs = connection.execute("SELECT * FROM demo_handoffs ORDER BY id").fetchall()
    appointments = connection.execute(
        "SELECT conversation_id, scheduled_at, calendar_status FROM demo_appointments ORDER BY id"
    ).fetchall()

    connection.close()

    site_only = scope != "all"
    appointment_by_conversation = {a["conversation_id"]: dict(a) for a in appointments}
    handoffs_by_conversation = defaultdict(list)
    conversation_ids = {c["id"] for c in conversations}

    for handoff in handoffs:
        if handoff["vertical"] != "inmobiliaria" and handoff["conversation_id"] in conversation_ids:
            handoffs_by_conversation[handoff["conversation_id"]].append(dict(handoff))

    rows = []

    for conversation in conversations:
        if vertical and conversation["vertical"] != vertical:
            continue

        if site_only and conversation["source"] != "widget":
            continue

        lead = json.loads(conversation["lead_data"] or "{}")
        linked = handoffs_by_conversation.get(conversation["id"], [])
        name, phone, email = lead.get("name"), lead.get("phone"), lead.get("email")

        for handoff in linked:
            name = name or handoff["name"]

            if handoff["contact_type"] == "phone" and not phone:
                phone = handoff["contact"]
            elif handoff["contact_type"] == "email" and not email:
                email = handoff["contact"]

        if not include_incomplete and not (phone or email):
            continue

        rows.append(_row(
            f"c-{conversation['id']}", "conversation", conversation["vertical"], conversation["source"],
            conversation["created_at"], conversation["updated_at"], lead, name, phone, email,
            conversation["lead_status"], conversation["lead_note"],
            conversation["status"] == "completed", linked,
            appointment_by_conversation.get(conversation["id"]),
        ))

    linked_handoff_ids = {h["id"] for group in handoffs_by_conversation.values() for h in group}

    for handoff in handoffs:
        if handoff["id"] in linked_handoff_ids:
            continue

        if vertical and handoff["vertical"] != vertical:
            continue

        if site_only and handoff["source"] != "widget":
            continue

        lead = {}

        if handoff["vertical"] == "inmobiliaria" and handoff["conversation_id"] is not None:
            conversation = conversation_repository.get_conversation(handoff["conversation_id"])
            lead = (conversation or {}).get("lead_data") or {}

        is_phone = handoff["contact_type"] == "phone"

        rows.append(_row(
            f"h-{handoff['id']}", "handoff", handoff["vertical"], handoff["source"],
            handoff["created_at"], handoff["created_at"], lead, handoff["name"],
            handoff["contact"] if is_phone else None,
            None if is_phone else handoff["contact"],
            handoff["lead_status"], handoff["lead_note"], False, [dict(handoff)], None,
        ))

    counts = {name: 0 for name in STATUSES}

    for row in rows:
        counts[row["status"]] += 1

    counts["total"] = len(rows)

    if status:
        rows = [row for row in rows if row["status"] == status]

    rows.sort(key=lambda row: row["updated_at"] or "", reverse=True)
    rows.sort(key=lambda row: not row["urgent"])
    rows.sort(key=lambda row: STATUS_RANK[row["status"]])

    return {"leads": rows, "counts": counts}


def set_status(lead_id: str, status: str, note: str | None) -> bool:
    """Devuelve False si el lead no existe. Lanza ValueError si el dato no es válido."""

    if status not in STATUSES:
        raise ValueError("Estado no válido: usa nuevo, contactado o cerrado.")

    kind, _, raw_id = lead_id.partition("-")
    table = TABLE_BY_KIND.get(kind)

    if table is None or not raw_id.isdigit():
        raise ValueError("Identificador de lead no válido.")

    connection = get_connection()

    if note is None:
        cursor = connection.execute(
            f"UPDATE {table} SET lead_status = ? WHERE id = ?", (status, int(raw_id))
        )
    else:
        cursor = connection.execute(
            f"UPDATE {table} SET lead_status = ?, lead_note = ? WHERE id = ?",
            (status, note.strip() or None, int(raw_id)),
        )

    connection.commit()
    updated = cursor.rowcount > 0
    connection.close()

    return updated


def _csv_safe(value: str) -> str:
    """
    Evita que Excel ejecute como fórmula un texto escrito por un visitante
    ("=HIPERVINCULO(...)"). Los teléfonos con "+" se respetan.
    """

    if value.startswith(("=", "@", "\t", "\r")):
        return "'" + value

    if value.startswith(("+", "-")) and not PHONE_LIKE.match(value):
        return "'" + value

    return value


def leads_to_csv(leads: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)

    for lead in leads:
        appointment = lead["appointment"]
        details = "; ".join(f"{d['label']}: {d['value']}" for d in lead["details"])

        cells = [
            (lead["created_at"] or "").replace("T", " ").rstrip("Z"),
            lead["vertical_label"],
            "Web del cliente" if lead["source"] == "widget" else "Prueba de demo",
            lead["status"],
            "sí" if lead["urgent"] else "",
            lead["name"],
            lead["phone"],
            lead["email"],
            details,
            appointment["scheduled_at"] if appointment else "",
            lead["note"],
        ]

        writer.writerow([_csv_safe(str(cell)) for cell in cells])

    return "﻿" + buffer.getvalue()
