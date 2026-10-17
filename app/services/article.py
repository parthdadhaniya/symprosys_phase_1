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
    @staticmethod
    async def get_article(db: AsyncSession, article_id: int) -> Optional[Article]:
        return await article_crud.get(db, article_id=article_id)

    @staticmethod
    async def get_article_by_url(db: AsyncSession, url: str) -> Optional[Article]:
        return await article_crud.get_by_url(db, url=url)

    @staticmethod
    async def list_articles(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        company_name: Optional[str] = None,
        status: Optional[ArticleStatus] = None,
    ) -> Tuple[List[Article], int]:
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

        # Dispatch async processing (Celery with fallback to BackgroundTasks)
        ArticleService.dispatch_processing_task(
            article_id=article.id, background_tasks=background_tasks
        )

        return article

    @staticmethod
    def dispatch_processing_task(
        article_id: int, background_tasks: Optional[BackgroundTasks] = None
    ):
        """
        Dispatches article processing to Celery worker.
        Gracefully falls back to FastAPI BackgroundTasks if Celery broker is unavailable.
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
        return await article_crud.delete(db, article_id=article_id)
