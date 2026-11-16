"""Main FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    yield
    # Shutdown actions


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    description="Smart Expense Management with Hybrid OCR (Google Vision & Gemini Flash)",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Liveness probe: verifies that the web service process is active (TC-01-02)."""
    return {
        "status": "ok",
        "app": "smart-expense-ocr",
        "version": settings.APP_VERSION,
        "git_sha": settings.GIT_SHA,
    }


@app.get("/api/v1/ready", tags=["System"])
async def readiness_check() -> JSONResponse:
    """Readiness probe: verifies connectivity to backend database and services (TC-01-05)."""
    try:
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "connected",
                "version": settings.APP_VERSION,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "detail": str(e),
            },
        )


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to Kexpense Smart OCR API", "docs": "/docs"}
