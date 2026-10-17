"""Service layer managing article business logic, validations, and async task dispatching.

Coordinates between the REST controllers, CRUD database operations, and
asynchronous processing workers (Celery with fallback to BackgroundTasks).
"""

import logging
from typing import List, Optional, Tuple
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.article import article_crud
from app.models.article import Article, ArticleStatus
from app.schemas.article import ArticleCreate, ArticleUpdate

logger = logging.getLogger(__name__)


class ArticleService:
    """Business service coordinating article operations, validations, and background queueing."""

    @staticmethod
    async def get_article(db: AsyncSession, article_id: int) -> Optional[Article]:
        """Retrieve an article by its primary key ID.

        Args:
            db (AsyncSession): Database session.
            article_id (int): Primary key ID.

        Returns:
            Optional[Article]: The Article entity if found, else None.
        """
        return await article_crud.get(db, article_id=article_id)

    @staticmethod
    async def get_article_by_url(db: AsyncSession, url: str) -> Optional[Article]:
        """Retrieve an article by its unique URL.

        Args:
            db (AsyncSession): Database session.
            url (str): Article URL.

        Returns:
            Optional[Article]: The Article entity if found, else None.
        """
        return await article_crud.get_by_url(db, url=url)

    @staticmethod
    async def list_articles(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        company_name: Optional[str] = None,
        status: Optional[ArticleStatus] = None,
    ) -> Tuple[List[Article], int]:
        """List articles with pagination and optional filtering.

        Args:
            db (AsyncSession): Database session.
            skip (int): Offset for pagination.
            limit (int): Number of items per page.
            company_name (Optional[str]): Company name filter.
            status (Optional[ArticleStatus]): Status filter.

        Returns:
            Tuple[List[Article], int]: List of articles and total matching count.
        """
        return await article_crud.get_multi_with_filters(
            db=db,
            skip=skip,
            limit=limit,
            company_name=company_name,
            status=status,
        )

    @staticmethod
    async def create_article(
        db: AsyncSession,
        article_in: ArticleCreate,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Article:
        """Create a new article and dispatch asynchronous classification and summarization.

        Args:
            db (AsyncSession): Database session.
            article_in (ArticleCreate): Validated creation schema.
            background_tasks (Optional[BackgroundTasks]): FastAPI BackgroundTasks instance for fallback.

        Raises:
            HTTPException: 409 Conflict if an article with the same URL already exists.

        Returns:
            Article: The newly created Article record.
        """
        # Pre-check for duplicate URL
        existing = await article_crud.get_by_url(db, url=str(article_in.url))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Article with URL '{article_in.url}' already exists.",
            )

        try:
            article = await article_crud.create(db, obj_in=article_in)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Article with URL '{article_in.url}' already exists.",
            )

        # Dispatch async processing (Celery worker with fallback to BackgroundTasks)
        ArticleService.dispatch_processing_task(
            article_id=article.id, background_tasks=background_tasks
        )

        return article

    @staticmethod
    def dispatch_processing_task(
        article_id: int, background_tasks: Optional[BackgroundTasks] = None
    ) -> None:
        """Dispatch article processing to Celery worker or fallback to FastAPI BackgroundTasks.

        Args:
            article_id (int): ID of the article to process.
            background_tasks (Optional[BackgroundTasks]): Local background queue if Celery is offline.
        """
        try:
            from app.tasks.article_tasks import process_article_task
            process_article_task.delay(article_id)
            logger.info(f"Dispatched Celery task for article {article_id}.")
        except Exception as exc:
            logger.warning(
                f"Celery broker unavailable ({exc}). Falling back to local BackgroundTasks."
            )
            if background_tasks is not None:
                from app.tasks.article_tasks import process_article_sync
                background_tasks.add_task(process_article_sync, article_id)

    @staticmethod
    async def update_article(
        db: AsyncSession, article: Article, article_in: ArticleUpdate
    ) -> Article:
        """Update an existing article entity.

        Args:
            db (AsyncSession): Database session.
            article (Article): Existing Article entity.
            article_in (ArticleUpdate): Updated fields.

        Raises:
            HTTPException: 409 Conflict if new URL already exists on another article.

        Returns:
            Article: The updated Article entity.
        """
        if article_in.url and str(article_in.url) != article.url:
            existing = await article_crud.get_by_url(db, url=str(article_in.url))
            if existing and existing.id != article.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Article with URL '{article_in.url}' already exists.",
                )

        try:
            return await article_crud.update(db, db_obj=article, obj_in=article_in)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Update violates database constraints.",
            )

    @staticmethod
    async def delete_article(db: AsyncSession, article_id: int) -> Optional[Article]:
        """Delete an article by ID.

        Args:
            db (AsyncSession): Database session.
            article_id (int): ID of the article.

        Returns:
            Optional[Article]: The deleted Article or None if not found.
        """
        return await article_crud.delete(db, article_id=article_id)
