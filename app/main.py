"""FastAPI main application module.

Initializes the FastAPI application instance, configures CORS middleware,
manages startup and shutdown lifespans (table schema initialization and connection disposal),
and registers API routers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import articles
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    On startup:
        Initializes database tables defined on the SQLAlchemy declarative Base.
    On shutdown:
        Gracefully closes and disposes pooled async database engine connections.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Backend service for ingesting, classifying, summarizing, and querying "
        "news articles for companies asynchronously."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration: mount under versioned path (/api/v1/articles) and root (/articles)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(articles.router, prefix="/articles", tags=["articles"])


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_model=Dict[str, str],
)
async def health_check() -> Dict[str, str]:
    """Perform a simple health check to verify service availability.

    Returns:
        dict: A dictionary containing health status and application name.
    """
    return {"status": "ok", "app": settings.PROJECT_NAME}
