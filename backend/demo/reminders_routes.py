from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.demo import reminders
from backend.routes.study_leads import _check_admin_key

router = APIRouter()

_PAGE = (
    "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Baja</title></head>"
    "<body style='font-family:system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1.5rem;line-height:1.5'>"
    "<h1 style='font-size:1.4rem'>{title}</h1><p>{text}</p></body></html>"
)


class OptOut(BaseModel):
    email: str = Field(max_length=200)


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(e: str = "", t: str = ""):
    """Enlace de baja de los correos de seguimiento (firmado, sin iniciar sesión)."""

    if not e or not reminders.valid_token(e, t):
        return HTMLResponse(
            _PAGE.format(title="Enlace no válido", text="No hemos podido procesar la baja. Responde al correo y lo gestionamos."),
            status_code=400,
        )

    reminders.opt_out(e)

    return HTMLResponse(
        _PAGE.format(title="Listo, te hemos dado de baja", text="No recibirás más mensajes de seguimiento.")
    )


@router.post("/admin/reminders/run")
def run_reminders(key: str | None = None, dry_run: bool = True):
    """
    Con dry_run=true (por defecto) muestra qué se enviaría ahora mismo, sin
    enviar nada. Con dry_run=false fuerza un repaso real (requiere REMINDERS_ENABLED).
    """

    _check_admin_key(key)

    if not dry_run and not reminders.enabled():
        raise HTTPException(status_code=409, detail="Los recordatorios están desactivados (REMINDERS_ENABLED).")

    return reminders.run_once(dry_run=dry_run)


@router.post("/admin/reminders/optout")
def admin_opt_out(request: OptOut, key: str | None = None):
    """Para cuando alguien responde «BAJA» al correo: el negocio lo apunta aquí."""

    _check_admin_key(key)
    reminders.opt_out(request.email)

    return {"ok": True}
