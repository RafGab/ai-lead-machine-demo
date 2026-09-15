from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes.properties import router as properties_router
from backend.routes.search import router as search_router
from backend.routes.conversation import router as conversation_router
from backend.routes.visits import router as visits_router
from backend.routes.webhooks import router as webhooks_router
from backend.database.database import create_tables



app = FastAPI()

app.mount("/properties", StaticFiles(directory="frontend/public/properties"), name="properties")

create_tables()  # Create tables if they don't exist

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