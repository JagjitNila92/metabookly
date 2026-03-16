import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.engine import init_engine, close_engine
from app.api.v1.health import router as health_router
from app.api.v1.router import router as v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    logger.info("Starting Metabookly API (environment: %s)", settings.environment)
    database_url = settings.resolve_database_url()
    init_engine(
        database_url=database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    logger.info("Database engine ready")
    yield
    # Shutdown
    await close_engine()
    logger.info("Database engine closed")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Metabookly API",
        description="AI-powered book discovery and ordering platform for retailers",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Updated with production URL at deploy time
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = create_app()
