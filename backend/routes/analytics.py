import json
import unicodedata
from collections import Counter
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.routes.study_leads import _check_admin_key
from backend.services.normalization import normalize_operation, normalize_property_type

router = APIRouter()

HOUR_LABELS_ES = {
    0: "medianoche", 3: "la madrugada", 6: "la mañana temprano", 9: "la mañana",
    12: "el mediodía", 15: "la tarde", 18: "la tarde-noche", 21: "la noche",
}


class PageViewRequest(BaseModel):
    page: str


@router.post("/analytics/pageview")
def track_pageview(request: PageViewRequest):
    connection = get_connection()

    connection.execute(
        "INSERT INTO page_views (page) VALUES (?)",
        (request.page,),
    )

    connection.commit()
    connection.close()

    return {"status": "ok"}


def _fold_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _hour_bucket(hour: int) -> tuple[int, str]:
    bucket_start = (hour // 3) * 3
    bucket_end = (bucket_start + 3) % 24
    label = f"{bucket_start:02d}:00–{bucket_end:02d}:00"
    return bucket_start, label


def _month_bounds(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/admin/insights")
def get_insights(key: str | None = None):
    _check_admin_key(key)

    now = datetime.now()
    month_start = _month_bounds(now)

    connection = get_connection()

    pageviews_total = connection.execute(
        "SELECT COUNT(*) AS n FROM page_views"
    ).fetchone()["n"]

    pageviews_month = connection.execute(
        "SELECT COUNT(*) AS n FROM page_views WHERE created_at >= ?",
        (month_start.isoformat(sep=" "),),
    ).fetchone()["n"]

    rows = connection.execute(
        "SELECT lead_data, created_at FROM conversations"
    ).fetchall()

    connection.close()

    city_counter = Counter()
    city_labels = {}
    operation_counter = Counter()
    property_type_counter = Counter()
    hour_counter = Counter()
    hour_labels = {}

    leads_total = 0
    leads_month = 0

    for row in rows:
        try:
            lead = json.loads(row["lead_data"] or "{}")
        except (json.JSONDecodeError, TypeError):
            lead = {}

        if not any(v not in (None, "", False) for v in lead.values()):
            continue

        try:
            created_at = datetime.fromisoformat(row["created_at"])
        except (ValueError, TypeError):
            created_at = None

        leads_total += 1
        is_this_month = created_at is not None and created_at >= month_start
        if is_this_month:
            leads_month += 1

        if lead.get("city"):
            city_key = _fold_accents(lead["city"].strip().lower())
            city_counter[city_key] += 1
            # Preferimos como etiqueta la primera variante que tenga
            # tilde/ñ (más probablemente bien escrita) si aparece luego.
            existing_label = city_labels.get(city_key)
            candidate_label = lead["city"].strip().title()
            if existing_label is None or (existing_label == _fold_accents(existing_label) and candidate_label != _fold_accents(candidate_label)):
                city_labels[city_key] = candidate_label
        if lead.get("operation"):
            try:
                operation_counter[normalize_operation(lead["operation"])] += 1
            except AttributeError:
                pass
        if lead.get("property_type"):
            try:
                property_type_counter[normalize_property_type(lead["property_type"])] += 1
            except AttributeError:
                pass

        if created_at is not None:
            bucket_start, label = _hour_bucket(created_at.hour)
            hour_counter[bucket_start] += 1
            hour_labels[bucket_start] = label

    narrative = []
    suggestions = []

    if pageviews_total > 0:
        narrative.append(
            f"Tu página ha tenido {pageviews_total} visitas en total"
            + (f", {pageviews_month} de ellas este mes." if pageviews_month else ".")
        )
    else:
        narrative.append(
            "Todavía no hay datos de visitas a la página — el conteo empieza a partir de ahora."
        )

    if leads_total > 0:
        narrative.append(
            f"Se han iniciado {leads_total} conversaciones con el agente en total"
            + (f", {leads_month} este mes." if leads_month else ".")
        )
    else:
        narrative.append("Todavía no hay conversaciones registradas con datos suficientes para analizar.")

    if city_counter:
        top_city_key, top_city_count = city_counter.most_common(1)[0]
        top_city = city_labels[top_city_key]
        share = top_city_count / sum(city_counter.values())
        narrative.append(
            f"La ciudad con más interés es {top_city}, con {top_city_count} de cada "
            f"{sum(city_counter.values())} solicitudes ({share:.0%})."
        )
        if share >= 0.4 and len(city_counter) > 1:
            second_city_key, _ = city_counter.most_common(2)[1]
            second_city = city_labels[second_city_key]
            suggestions.append(
                f"La mayoría del interés se concentra en {top_city}. Si tienes capacidad, "
                f"podrías reforzar tu oferta ahí, o promocionar más tu presencia en "
                f"{second_city}, que también genera interés pero recibe menos atención."
            )

    if operation_counter:
        top_operation, _ = operation_counter.most_common(1)[0]
        narrative.append(f"La mayoría de la gente busca: {top_operation}.")

    if property_type_counter:
        top_type, _ = property_type_counter.most_common(1)[0]
        narrative.append(f"El tipo de propiedad más consultado es: {top_type}.")

    if hour_counter:
        top_hour_start, top_hour_n = hour_counter.most_common(1)[0]
        top_label = hour_labels[top_hour_start]
        share = top_hour_n / sum(hour_counter.values())
        narrative.append(
            f"La franja con más actividad es entre las {top_label} "
            f"({share:.0%} de los contactos)."
        )
        if share >= 0.35:
            suggestions.append(
                f"Podrías conseguir más clientes si refuerzas la atención (o la rapidez de "
                f"respuesta) entre las {top_label} — es cuando más te contactan."
            )

    if not suggestions:
        suggestions.append(
            "Todavía no hay suficientes datos para sugerencias concretas. "
            "Vuelve a revisar este panel dentro de unas semanas, cuando haya más actividad."
        )

    return {
        "period": now.strftime("%B %Y"),
        "pageviews_total": pageviews_total,
        "pageviews_month": pageviews_month,
        "leads_total": leads_total,
        "leads_month": leads_month,
        "top_cities": [
            [city_labels[key], count] for key, count in city_counter.most_common(5)
        ],
        "top_operations": operation_counter.most_common(5),
        "top_property_types": property_type_counter.most_common(5),
        "busiest_hours": [
            {"label": hour_labels[h], "count": n}
            for h, n in hour_counter.most_common(5)
        ],
        "narrative": narrative,
        "suggestions": suggestions,
    }
