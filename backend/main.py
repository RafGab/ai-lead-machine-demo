from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.properties import router as properties_router
from backend.routes.search import router as search_router
from backend.routes.conversation import router as conversation_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {
        "mensaje": "AI Lead Machine está funcionando 🚀"
    }


app.include_router(properties_router)
app.include_router(search_router)
app.include_router(conversation_router)