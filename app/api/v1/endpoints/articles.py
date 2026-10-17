from typing import Optional
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
):
    """
    Create a new article and queue it for asynchronous classification and summarization.
    
    - **company_name**: Name of the company (required)
    - **title**: Article title (required)
    - **url**: Article URL (must be unique HTTP/HTTPS URL)
    - **content**: Full text content (optional)
    - **status**: Status ('Pending', 'Processing', 'Completed', 'Failed')
    - **category**: Article category (optional)
    - **summary**: Article summary (optional)
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
):
    """
    Trigger or retry asynchronous classification and summarization for a specific article.
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
    status: Optional[ArticleStatus] = Query(
        None,
        description="Filter by article status: Pending, Processing, Completed, Failed",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve articles with pagination and optional filters.
    
    - **page**: Page number (default: 1)
    - **limit**: Page size limit (default: 10, max: 100)
    - **skip**: Optional raw offset override
    - **company_name**: Optional company name filter
    - **status**: Optional status filter
    """
    calculated_skip = skip if skip is not None else (page - 1) * limit
    current_page = (calculated_skip // limit) + 1

    items, total = await ArticleService.list_articles(
        db=db,
        skip=calculated_skip,
        limit=limit,
        company_name=company_name,
        status=status,
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
):
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
):
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
):
    article = await ArticleService.get_article(db=db, article_id=article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with id {article_id} not found",
        )
    await ArticleService.delete_article(db=db, article_id=article_id)
    return None
