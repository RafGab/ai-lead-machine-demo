import logging
import os

from fastapi import APIRouter, HTTPException, Query, Request, Response

from backend.services import facebook_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/facebook")
def verify_facebook_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    """
    Endpoint de verificación que Meta llama una vez al configurar
    el webhook de Lead Ads (debe devolver hub.challenge tal cual).
    """

    expected_token = os.getenv("FACEBOOK_VERIFY_TOKEN")

    if (
        expected_token
        and hub_mode == "subscribe"
        and hub_verify_token == expected_token
    ):
        return Response(content=hub_challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verificación de webhook fallida.")


@router.post("/webhooks/facebook")
async def receive_facebook_lead(request: Request):
    """
    Recibe las notificaciones de nuevos leads de Meta Lead Ads.
    La notificación solo trae el leadgen_id; los datos reales del
    formulario se piden aparte a la Graph API.
    """

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            leadgen_id = change.get("value", {}).get("leadgen_id")

            if not leadgen_id:
                continue

            try:
                facebook_service.process_lead(leadgen_id)
            except Exception:
                logger.exception(
                    "Error procesando el lead de Facebook %s",
                    leadgen_id,
                )

    return {"status": "received"}
