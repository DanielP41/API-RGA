from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import get_settings
from app.api import routes, routes_documents
from app.utils.logging import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas de la API e incluyes
app.include_router(routes.router, prefix="/api/v1")
app.include_router(routes_documents.router, prefix="/api/v1")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Servir archivos estáticos (Frontend) - Debe ser el último para no interferir con las rutas de la API
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
