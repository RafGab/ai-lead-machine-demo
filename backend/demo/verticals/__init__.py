from backend.demo.verticals import dental, despacho, hotel, gimnasio

# "inmobiliaria" no está aquí: usa directamente el motor real de
# backend/services (ver backend/demo/orchestrator.py) para que la demo
# muestre el producto insignia tal cual funciona en producción.
GENERIC_VERTICALS = {
    "dental": dental,
    "despacho": despacho,
    "hotel": hotel,
    "gimnasio": gimnasio,
}

INMOBILIARIA_META = {
    "label": "Inmobiliaria",
    "icon": "🏠",
    "color": "#7f1626",
    "welcome": "¡Hola! Soy tu asistente inmobiliario. ¿Buscas alquilar o comprar?",
}


def list_verticals() -> list[dict]:
    verticals = [{"key": "inmobiliaria", **INMOBILIARIA_META}]

    for key, module in GENERIC_VERTICALS.items():
        verticals.append({
            "key": key,
            "label": module.LABEL,
            "icon": module.ICON,
            "color": module.COLOR,
            "welcome": module.WELCOME,
        })

    return verticals
