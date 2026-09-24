# Campos que nunca se agrupan en las estadísticas por rubro: son datos
# personales del lead, no categorías de interés.
PII_FIELDS = {"name", "phone", "email"}

# Etiquetas en español para los campos más comunes de los rubros de la
# demo. Un campo que no esté aquí se muestra con su nombre tal cual
# (para no bloquear rubros nuevos que se añadan después).
FIELD_LABELS = {
    "name": "nombre",
    "phone": "teléfono",
    "email": "correo",
    "operation": "operación",
    "property_type": "tipo de inmueble",
    "city": "ciudad",
    "max_price": "presupuesto máximo",
    "move_in_date": "fecha de entrada",
    "bedrooms": "habitaciones",
    "bathrooms": "baños",
    "occupants": "ocupantes",
    "has_minors": "menores",
    "has_pets": "mascotas",
    "procedure": "trámite",
    "current_country": "país de residencia",
    "nationality": "nacionalidad",
    "education_level": "nivel de estudios",
    "contact_hours": "horario de contacto",
    "goal": "objetivo",
    "membership_type": "tipo de membresía",
    "preferred_schedule": "horario preferido",
    "room_type": "tipo de habitación",
    "area": "área",
    "specialty": "especialidad",
    "current_status": "estado del piso",
}
