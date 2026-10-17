"""REST API router endpoints for Article ingestion, pagination, filtering, and management.

Provides handlers for:
- POST /articles: Create new article and enqueue async processing.
- POST /articles/{id}/process: Manually trigger or retry async processing.
- GET /articles: Paginated article retrieval with company name and status filters.
- GET /articles/{id}: Retrieve single article by ID.
- PUT /articles/{id}: Partial or full article update.
- DELETE /articles/{id}: Delete article by ID.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.article import ArticleStatus
from app.schemas.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
    PaginatedArticleResponse,
)
from app.services.article import ArticleService

router = APIRouter()


@router.post(
    "",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new article and dispatch asynchronous processing",
    responses={
        201: {"description": "Article created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Article with this URL already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_article(
    article_in: ArticleCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Create a new article and queue it for asynchronous classification and summarization.

    Args:
        article_in (ArticleCreate): Article payload.
        background_tasks (BackgroundTasks): Local background task queue for fallback.
        db (AsyncSession): Injected async database session.

    Returns:
        ArticleResponse: Newly created article in 'Pending' state.
    """
    return await ArticleService.create_article(
        db=db, article_in=article_in, background_tasks=background_tasks
    )


@router.post(
    "/{article_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger or retry asynchronous processing for an article",
    responses={
        202: {"description": "Article processing queued"},
        404: {"description": "Article not found"},
    },
)
async def trigger_article_processing(
    article_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger or retry asynchronous classification and summarization for a specific article.

    Args:
        article_id (int): Primary key ID of the article to process.
        background_tasks (BackgroundTasks): Local background task queue for fallback.
        db (AsyncSession): Injected async database session.

    Raises:
        HTTPException: 404 Not Found if the article ID does not exist.

    Returns:
        Dict[str, Any]: Confirmation message and article status.
    """
    article = await ArticleService.get_article(db=db, article_id=article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with id {article_id} not found",
        )
    ArticleService.dispatch_processing_task(
        article_id=article.id, background_tasks=background_tasks
    )
    return {
        "message": "Article processing task queued",
        "article_id": article_id,
        "status": article.status,
    }


@router.get(
    "",
    response_model=PaginatedArticleResponse,
    status_code=status.HTTP_200_OK,
    summary="List articles with pagination and filters",
    responses={
        200: {"description": "Paginated list of articles"},
        422: {"description": "Validation error on query parameters"},
    },
)
async def list_articles(
    response: Response,
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(10, ge=1, le=100, description="Number of articles per page (max 100)"),
    skip: Optional[int] = Query(None, ge=0, description="Offset override (optional)"),
    company_name: Optional[str] = Query(
        None,
        min_length=1,
        max_length=255,
        description="Filter by company name (case-insensitive substring match)",
    ),
    status_filter: Optional[ArticleStatus] = Query(
        None,
        alias="status",
        description="Filter by article status: Pending, Processing, Completed, Failed",
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedArticleResponse:
    """Retrieve articles with pagination and optional filters.

    Args:
        response (Response): FastAPI response to attach headers.
        page (int): Page number (1-indexed).
        limit (int): Items per page.
        skip (Optional[int]): Optional offset override.
        company_name (Optional[str]): Company substring filter.
        status_filter (Optional[ArticleStatus]): Article processing status filter.
        db (AsyncSession): Injected async database session.

    Returns:
        PaginatedArticleResponse: Enveloped response containing total count, page, items.
    """
    calculated_skip = skip if skip is not None else (page - 1) * limit
    current_page = (calculated_skip // limit) + 1

    items, total = await ArticleService.list_articles(
        db=db,
        skip=calculated_skip,
        limit=limit,
        company_name=company_name,
        status=status_filter,
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 0
    response.headers["X-Total-Count"] = str(total)

    return PaginatedArticleResponse(
        total=total,
        page=current_page,
        limit=limit,
        total_pages=total_pages,
        items=items,
    )


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an article by ID",
    responses={
        200: {"description": "Article details"},
        404: {"description": "Article not found"},
    },
)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Retrieve details of a single article by ID.

    Args:
        article_id (int): Primary key ID of the article.
        db (AsyncSession): Injected async database session.

    Raises:
        HTTPException: 404 Not Found if article is missing.

    Returns:
        ArticleResponse: Complete article details.
    """
    article = await ArticleService.get_article(db=db, article_id=article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with id {article_id} not found",
        )
    return article


@router.put(
    "/{article_id}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an article by ID",
    responses={
        200: {"description": "Article updated successfully"},
        404: {"description": "Article not found"},
        409: {"description": "URL conflict with existing article"},
    },
)
async def update_article(
    article_id: int,
    article_in: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Update attributes of an existing article.

    Args:
        article_id (int): ID of the article to update.
        article_in (ArticleUpdate): Updated field values.
        db (AsyncSession): Injected async database session.

    Raises:
        HTTPException: 404 if not found, 409 if URL conflicts with another record.

    Returns:
        ArticleResponse: The updated article representation.
    """
    article = await ArticleService.get_article(db=db, article_id=article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with id {article_id} not found",
        )
    return await ArticleService.update_article(
        db=db, article=article, article_in=article_in
    )


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an article by ID",
    responses={
        204: {"description": "Article deleted successfully"},
        404: {"description": "Article not found"},
    },
)
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an article from the database.

    Args:
        article_id (int): ID of the article to delete.
        db (AsyncSession): Injected async database session.

    Raises:
        HTTPException: 404 if article does not exist.
    """
    article = await ArticleService.get_article(db=db, article_id=article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with id {article_id} not found",
        )
    await ArticleService.delete_article(db=db, article_id=article_id)
    return None
