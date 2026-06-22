"""
FastAPI application entrypoint.

Wires together configuration, logging, database/Redis lifecycle, middleware,
and the v1 API router. No business logic lives here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.db.redis import close_redis_pool, init_redis_pool
from app.db.session import engine
from app.middleware.exception_middleware import ExceptionHandlingMiddleware
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting %s (env=%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    await init_redis_pool()

    yield

    # --- Shutdown ---
    logger.info("Shutting down %s", settings.PROJECT_NAME)
    await close_redis_pool()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Custom middleware (order matters: outermost = last added)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ExceptionHandlingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"], summary="Service liveness check")
    async def root():
        return {
            "service": settings.PROJECT_NAME,
            "status": "running",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health", tags=["Root"], summary="Health check")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()
