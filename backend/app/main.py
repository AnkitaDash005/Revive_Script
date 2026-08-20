from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.database.database import engine
from app.routers.ai import router as ai_router
from app.routers.auth import router as auth_router
from app.routers.collections import router as collection_router
from app.routers.manuscripts import router as manuscript_router
from app.routers.pages import router as page_router
from app.routers.provenance import router as provenance_router

app = FastAPI(
    title=settings.app_name,
    description="Heritage Manuscript Preservation and Reconstruction Platform",
    version="0.1.0",
)

# Path Configuration & Static Files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# STORAGE_DIR = BASE_DIR / "storage"
BACKEND_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BACKEND_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers (Prefixed with /api)
app.include_router(auth_router)                         # /auth
app.include_router(collection_router, prefix="/api")    # /api/collections
app.include_router(manuscript_router, prefix="/api")    # /api/collections/{id}/manuscripts
app.include_router(page_router, prefix="/api")          # /api/pages
app.include_router(provenance_router, prefix="/api")    # /api/provenance
app.include_router(ai_router, prefix="/api")            # /api/ai

# Frontend HTML Page Routes
@app.get("/", include_in_schema=False)
@app.get("/login", include_in_schema=False)
def serve_login():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/collections", include_in_schema=False)
def serve_collections():
    return FileResponse(FRONTEND_DIR / "collections.html")


@app.get("/collection-detail", include_in_schema=False)
def serve_collection_detail():
    return FileResponse(FRONTEND_DIR / "collection-detail.html")


@app.get("/manuscripts", include_in_schema=False)
def serve_manuscripts():
    return FileResponse(FRONTEND_DIR / "manuscripts.html")


@app.get("/manuscript-detail", include_in_schema=False)
def serve_manuscript_detail():
    return FileResponse(FRONTEND_DIR / "manuscript-detail.html")


@app.get("/page-detail", include_in_schema=False)
def serve_page_detail():
    return FileResponse(FRONTEND_DIR / "page-detail.html")


@app.get("/provenance", include_in_schema=False)
def serve_provenance():
    return FileResponse(FRONTEND_DIR / "provenance.html")


@app.get("/reconstruction-detail", include_in_schema=False)
def serve_reconstruction_detail():
    return FileResponse(FRONTEND_DIR / "reconstruction-detail.html")


@app.get("/search", include_in_schema=False)
def serve_search():
    return FileResponse(FRONTEND_DIR / "search.html")


@app.get("/settings", include_in_schema=False)
def serve_settings():
    return FileResponse(FRONTEND_DIR / "settings.html")


# Health Checks
@app.get("/api/info")
def api_info():
    return {"message": "Welcome to Revive_Script API", "version": "0.1.0"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}