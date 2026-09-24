from backend.demo.verticals import dental, despacho, hotel, gimnasio, propietarios, extranjeria

# "inmobiliaria" no está aquí: usa directamente el motor real de
# backend/services (ver backend/demo/orchestrator.py) para que la demo
# muestre el producto insignia tal cual funciona en producción.
GENERIC_VERTICALS = {
    "dental": dental,
    "despacho": despacho,
    "hotel": hotel,
    "gimnasio": gimnasio,
    "extranjeria": extranjeria,
    # "propietarios" es un segundo flujo DENTRO de Inmobiliaria (captación
    # de propietarios para gestión, no búsqueda de vivienda). No se lista
    # en list_verticals(): el frontend lo activa con un botón dentro de
    # la pestaña de Inmobiliaria, no como rubro aparte.
    "propietarios": propietarios,
}

# Subconjunto de GENERIC_VERTICALS que sí se listan como rubro propio en
# el selector principal (excluye "propietarios", que se activa desde un
# botón dentro de la pestaña de Inmobiliaria, no como rubro aparte).
_LISTED_KEYS = ["dental", "despacho", "hotel", "gimnasio", "extranjeria"]

INMOBILIARIA_META = {
    "label": "Inmobiliaria",
    "icon": "🏠",
    "color": "#7f1626",
    "welcome": "¡Hola! Soy tu asistente inmobiliario. ¿Buscas alquilar o comprar?",
}


def vertical_label(key: str) -> str:
    if key == "inmobiliaria":
        return INMOBILIARIA_META["label"]

    module = GENERIC_VERTICALS.get(key)

    return module.LABEL if module else key


def list_verticals() -> list[dict]:
    verticals = [{"key": "inmobiliaria", **INMOBILIARIA_META}]

    for key in _LISTED_KEYS:
        module = GENERIC_VERTICALS[key]
        verticals.append({
            "key": key,
            "label": module.LABEL,
            "icon": module.ICON,
            "color": module.COLOR,
            "welcome": module.WELCOME,
        })

    return verticals
