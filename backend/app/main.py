from fastapi import FastAPI
from sqlalchemy import text  # type: ignore[import-not-found]

from app.core.config import settings
from app.database.database import engine
from app.routers.auth import router as auth_router
from app.routers.collections import router as collection_router
from app.routers.manuscripts import router as manuscript_router
from app.routers.pages import router as page_router

app=FastAPI(
    title=settings.app_name,
    description="Heritage Manuscript Preservation and Reconstruction Platform",
    version="0.1.0"
)
app.include_router(auth_router)
app.include_router(collection_router)
app.include_router(manuscript_router)
app.include_router(page_router)


@app.get("/")
def root():
    return{
        "message":"Welcome to Revive_Script API",
        "version":"0.1.0"
    }

@app.get("/health")
def health_check():
    return{
        "status":"ok",
        "service":settings.app_name,
        "environment":settings.app_env,
    }

@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return{
            "status":"ok",
            "database":"connected"
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(e),
        }