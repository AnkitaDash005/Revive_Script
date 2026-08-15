from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.database.database import engine
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

# Configure SessionMiddleware for OAuth redirect handling over HTTP
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="session",
    same_site="lax",       # Allows cross-site redirects to read session cookies
    https_only=False,      # Set to False for local HTTP development
    max_age=3600,          # Cookie expiration in seconds (1 hour)
)

app.include_router(auth_router)
app.include_router(collection_router)
app.include_router(manuscript_router)
app.include_router(page_router)
app.include_router(provenance_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Revive_Script API",
        "version": "0.1.0",
    }


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
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(e),
        }