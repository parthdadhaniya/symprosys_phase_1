"""CRUD (Create, Read, Update, Delete) database access layer for Article entities.

Encapsulates all asynchronous SQLAlchemy queries, filtering, pagination logic,
and transactional persistence operations.
"""

from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleStatus
from app.schemas.article import ArticleCreate, ArticleUpdate


class CRUDArticle:
    """Data access object providing async database operations for articles."""

    async def get(self, db: AsyncSession, article_id: int) -> Optional[Article]:
        """Fetch an article by its primary key ID.

        Args:
            db (AsyncSession): The asynchronous database session.
            article_id (int): ID of the article to retrieve.

        Returns:
            Optional[Article]: The Article ORM object if found, otherwise None.
        """
        result = await db.execute(select(Article).where(Article.id == article_id))
        return result.scalars().first()

    async def get_by_url(self, db: AsyncSession, url: str) -> Optional[Article]:
        """Fetch an article by its exact unique URL.

        Args:
            db (AsyncSession): The asynchronous database session.
            url (str): The unique URL string.

        Returns:
            Optional[Article]: The Article ORM object if found, otherwise None.
        """
        result = await db.execute(select(Article).where(Article.url == url))
        return result.scalars().first()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        company_name: Optional[str] = None,
        status: Optional[ArticleStatus] = None,
    ) -> Tuple[List[Article], int]:
        """Retrieve paginated articles with optional company name and status filters.

        Args:
            db (AsyncSession): The asynchronous database session.
            skip (int): Number of records to skip for pagination.
            limit (int): Maximum number of records to return.
            company_name (Optional[str]): Case-insensitive company name search pattern.
            status (Optional[ArticleStatus]): ArticleStatus filter enum.

        Returns:
            Tuple[List[Article], int]: A tuple containing the list of articles for
            the current page and the total count of matching articles.
        """
        query = select(Article)
        count_query = select(func.count(Article.id))

        if company_name:
            search_pattern = f"%{company_name.strip()}%"
            query = query.where(Article.company_name.ilike(search_pattern))
            count_query = count_query.where(Article.company_name.ilike(search_pattern))

        if status:
            status_val = status.value if isinstance(status, ArticleStatus) else str(status)
            query = query.where(Article.status == status_val)
            count_query = count_query.where(Article.status == status_val)

        # Get total matching records
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated items ordered by creation time descending
        query = query.order_by(Article.created_at.desc(), Article.id.desc()).offset(skip).limit(limit)
        items_result = await db.execute(query)
        items = list(items_result.scalars().all())

        return items, total

    async def create(self, db: AsyncSession, obj_in: ArticleCreate) -> Article:
        """Create and persist a new article record in the database.

        Args:
            db (AsyncSession): The asynchronous database session.
            obj_in (ArticleCreate): Validated creation schema.

        Returns:
            Article: The persisted Article ORM entity with generated ID and timestamps.
        """
        data = obj_in.model_dump()
        if isinstance(data.get("status"), ArticleStatus):
            data["status"] = data["status"].value
        db_obj = Article(**data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: Article, obj_in: ArticleUpdate
    ) -> Article:
        """Update an existing article with partial modifications.

        Args:
            db (AsyncSession): The asynchronous database session.
            db_obj (Article): The existing Article entity in session.
            obj_in (ArticleUpdate): The update schema with optional fields.

        Returns:
            Article: The refreshed, updated Article ORM entity.
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        if isinstance(update_data.get("status"), ArticleStatus):
            update_data["status"] = update_data["status"].value
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, article_id: int) -> Optional[Article]:
        """Delete an article from the database by its ID.

        Args:
            db (AsyncSession): The asynchronous database session.
            article_id (int): ID of the article to delete.

        Returns:
            Optional[Article]: The deleted Article object, or None if not found.
        """
        db_obj = await self.get(db, article_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj


article_crud = CRUDArticle()