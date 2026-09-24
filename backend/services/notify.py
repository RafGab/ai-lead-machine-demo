import logging
import os
import smtplib
import threading
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def notify_email_for(vertical: str | None = None) -> str | None:
    """
    Destinatario del aviso: NOTIFY_EMAIL_<RUBRO> si existe (cada negocio
    puede recibir los suyos), luego NOTIFY_EMAIL, y por último la propia
    cuenta que envía.
    """

    if vertical:
        specific = os.getenv(f"NOTIFY_EMAIL_{vertical.upper()}")
        if specific:
            return specific

    return os.getenv("NOTIFY_EMAIL") or os.getenv("SMTP_USER")


def _send(subject: str, body: str, to: str) -> None:
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    try:
        message = EmailMessage()
        # Los datos del visitante van en el asunto: sin saltos de línea
        # para que nadie pueda inyectar cabeceras de correo.
        message["Subject"] = " ".join(subject.split())
        message["From"] = smtp_user
        message["To"] = to
        message.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception:
        logger.exception("No se pudo enviar el aviso por correo (asunto=%r)", subject)


def send_notification(subject: str, body: str, to: str | None = None) -> bool:
    """
    Envía un aviso por Gmail SMTP en segundo plano, para no retrasar la
    respuesta del chat. Devuelve False si no hay SMTP configurado o
    destinatario; un fallo de envío solo se registra en el log, nunca
    interrumpe guardar el lead.
    """

    if not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASSWORD"):
        return False

    recipient = to or notify_email_for()

    if not recipient:
        return False

    threading.Thread(target=_send, args=(subject, body, recipient), daemon=True).start()
    return True
