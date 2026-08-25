from fastapi import FastAPI
from backend.routes.properties import router as properties_router
from backend.routes.search import router as search_router

app = FastAPI()


@app.get("/")
def inicio():
    return {
        "mensaje": "AI Lead Machine está funcionando 🚀"
    }


app.include_router(properties_router)
app.include_router(search_router)