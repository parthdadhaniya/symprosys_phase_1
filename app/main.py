from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import articles
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup / initialize tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup on shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include both versioned prefix (/api/v1/articles) and root prefix (/articles)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(articles.router, prefix="/articles", tags=["articles"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
