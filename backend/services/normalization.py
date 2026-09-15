OPERATION_MAP = {
    "compra": "venta",
    "venta": "venta",
    "alquiler": "alquiler",
}

PROPERTY_TYPE_MAP = {
    "piso": "vivienda",
    "apartamento": "vivienda",
    "casa": "vivienda",
    "chalet": "vivienda",
    "vivienda": "vivienda",
    "habitacion": "habitacion",
}


def normalize_operation(value: str) -> str:
    return OPERATION_MAP.get(value.lower(), value.lower())


def normalize_property_type(value: str) -> str:
    return PROPERTY_TYPE_MAP.get(value.lower(), value.lower())
