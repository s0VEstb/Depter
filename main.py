# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging.config

from config import settings
from app.utils.logging import LOGGING_CONFIG
from app.routes import upload, status, profile, users

logging.config.dictConfig(LOGGING_CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Depter API is starting up...")
    yield
    logging.info("Depter API is shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Depter API",
        description="AI-скоринг финансовых выписок | mBank Hackathon 2026",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # CORS — для MVP/демо разрешаем всё
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Роутеры
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(status.router, prefix="/api", tags=["status"])
    app.include_router(profile.router, prefix="/api", tags=["profile"])
    app.include_router(users.router, prefix="/api", tags=["users"])

    return app


app = create_app()