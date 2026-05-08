from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.ai_client import AIClient
from app.core.bootstrap import ensure_default_admin
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    for warning in settings.insecure_default_warnings():
        logger.warning(warning)
    await ensure_default_admin()
    app.state.ai_client = AIClient()
    try:
        yield
    finally:
        await app.state.ai_client.aclose()
        logger.info("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    register_exception_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    # Routers
    from app.admin.router import router as admin_router
    from app.claim.router import router as claim_router
    from app.credit.router import router as credit_router
    from app.item.router import router as item_router
    from app.match.router import router as match_router
    from app.notification.router import router as notification_router
    from app.user.router import router as user_router

    app.include_router(user_router, prefix=settings.API_V1_PREFIX)
    app.include_router(item_router, prefix=settings.API_V1_PREFIX)
    app.include_router(notification_router, prefix=settings.API_V1_PREFIX)
    app.include_router(credit_router, prefix=settings.API_V1_PREFIX)
    app.include_router(claim_router, prefix=settings.API_V1_PREFIX)
    app.include_router(match_router, prefix=settings.API_V1_PREFIX)
    app.include_router(admin_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
