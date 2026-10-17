from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleStatus
from app.schemas.article import ArticleCreate, ArticleUpdate


class CRUDArticle:
    async def get(self, db: AsyncSession, article_id: int) -> Optional[Article]:
        result = await db.execute(select(Article).where(Article.id == article_id))
        return result.scalars().first()

    async def get_by_url(self, db: AsyncSession, url: str) -> Optional[Article]:
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
        query = select(Article)
        count_query = select(func.count(Article.id))

        if company_name:
            search_pattern = f"%{company_name.strip()}%"
            query = query.where(Article.company_name.ilike(search_pattern))
            count_query = count_query.where(Article.company_name.ilike(search_pattern))

        if status:
            query = query.where(Article.status == status)
            count_query = count_query.where(Article.status == status)

        # Get total matching records
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated items ordered by creation time descending
        query = query.order_by(Article.created_at.desc(), Article.id.desc()).offset(skip).limit(limit)
        items_result = await db.execute(query)
        items = list(items_result.scalars().all())

        return items, total

    async def create(self, db: AsyncSession, obj_in: ArticleCreate) -> Article:
        db_obj = Article(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: Article, obj_in: ArticleUpdate
    ) -> Article:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, article_id: int) -> Optional[Article]:
        db_obj = await self.get(db, article_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj


article_crud = CRUDArticle()
