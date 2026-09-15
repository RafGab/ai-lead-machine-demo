# Ejemplo: mismo motor aplicado a una clínica dental

Esto demuestra que replicar el agente a otro sector es cambiar 4 archivos
concretos, no reconstruir la aplicación. Comparado con el vertical
inmobiliario (`backend/`):

## Se sustituyen (están en esta carpeta)

| Archivo aquí | Equivalente inmobiliario | Qué cambia |
|---|---|---|
| `models/patient.py` | `backend/models/lead.py` | Campos: motivo, especialidad, urgencia, seguro, en vez de ciudad/precio/habitaciones |
| `services/ai_service.py` | `backend/services/ai_service.py` | El prompt de extracción, y una instrucción extra: nunca dar consejo médico, solo recoger datos |
| `services/questions.py` | `backend/services/questions.py` | El orden de preguntas del flujo de intake |
| `services/rules.py` | `backend/services/rules.py` | La lógica de negocio: aquí decide prioridad en vez de filtrar por menores/mascotas |

## Se reutilizan sin tocar una línea

- `backend/services/conversation_repository.py` — guardar mensajes y conversación es idéntico.
- `backend/services/conversation_service.py` — la orquestación (guardar mensaje → extraer datos → fusionar → guardar → responder) es igual; solo cambiaría el nombre de las importaciones a los archivos de arriba.
- `backend/services/calendar_service.py` y `backend/services/visit_service.py` — ¡se reutilizan tal cual! Una cita dental es exactamente lo mismo que una "visita": comprobar disponibilidad en Google Calendar, si está ocupado sugerir alternativas, invitar al profesional. Solo cambia el texto ("Visita" → "Cita") en la descripción del evento.
- `backend/routes/*.py` y `backend/main.py` — misma estructura de endpoints, solo apuntando a los servicios nuevos.
- `frontend/public/widget.js` — el widget embebible no cambia nada de código, solo los atributos `data-color` / `data-agent-name` / `data-subtitle` al insertarlo en la web de la clínica.
- Lo único que no aplica: `matching.py` (buscar propiedades). Una clínica no tiene "catálogo" que filtrar — su equivalente es directamente comprobar la disponibilidad de la agenda, que ya cubre `calendar_service.py`.

## No incluido a propósito

No he duplicado `conversation_service.py`, `main.py`, las rutas ni la base
de datos: son literalmente el mismo código con imports distintos. Duplicarlos
aquí sería ruido, no prueba de nada. Cuando haya un cliente real de este
vertical, se cablean estos archivos igual que en `backend/` y se listo.
