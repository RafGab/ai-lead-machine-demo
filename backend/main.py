from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes.properties import router as properties_router
from backend.routes.search import router as search_router
from backend.routes.conversation import router as conversation_router
from backend.routes.visits import router as visits_router
from backend.routes.webhooks import router as webhooks_router
from backend.routes.study_leads import router as study_leads_router
from backend.routes.reviews import router as reviews_router
from backend.routes.admin_properties import router as admin_properties_router
from backend.demo.routes import router as demo_router
from backend.demo.repository import create_tables as create_demo_tables
from backend.database.database import create_tables
from backend.database.seed import seed_if_empty



app = FastAPI()

app.mount("/properties", StaticFiles(directory="frontend/public/properties"), name="properties")

create_tables()  # Create tables if they don't exist
create_demo_tables()  # Tablas aisladas para la demo comercial multi-rubro
seed_if_empty()  # Catálogo de ejemplo solo la primera vez (no pisa datos reales)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] porque el widget embebible se sirve desde este
    # backend pero se ejecuta en el dominio de cada cliente (su web
    # WordPress); no se usan cookies/credenciales, solo JSON.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {
        "mensaje": "AI Lead Machine está funcionando 🚀"
    }


@app.get("/widget.js")
def widget_script():
    return FileResponse(
        "frontend/public/widget.js",
        media_type="application/javascript",
    )


app.include_router(properties_router)
app.include_router(search_router)
app.include_router(conversation_router)
app.include_router(visits_router)
app.include_router(webhooks_router)
app.include_router(study_leads_router)
app.include_router(reviews_router)
app.include_router(admin_properties_router)
app.include_router(demo_router)