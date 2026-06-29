from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from devops_resolver.presentation.api.dependencies import get_container
from devops_resolver.presentation.api.routes import router
from devops_resolver.shared.config import get_settings
from devops_resolver.shared.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    container = get_container()
    await container.startup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Adaptive multi-agent DevOps incident resolver with streaming traces.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()
