"""SQLAlchemy ORM models for news articles and related enums.

Defines the Article database entity with explicit table arguments, unique constraints,
column types, indexes, and lifecycle statuses.
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from app.core.database import Base


class ArticleStatus(str, enum.Enum):
    """Lifecycle status enumeration for articles in the ingestion and processing pipeline."""

    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


def get_utc_now() -> datetime:
    """Return the current UTC datetime as a naive datetime object for PostgreSQL timestamp compatibility.

    Returns:
        datetime: Current UTC time with tzinfo stripped.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Article(Base):
    """SQLAlchemy model representing an ingested news article for a company.

    Attributes:
        id (int): Primary key, auto-incrementing integer identifier.
        company_name (str): Name of the company associated with the article.
        title (str): Headline or title of the article.
        url (str): Unique URL link to the original article source.
        content (str, optional): Full body text of the article.
        status (str): Processing state ('Pending', 'Processing', 'Completed', 'Failed').
        category (str, optional): Classified domain category (e.g., 'Automotive', 'Technology').
        summary (str, optional): Generated extractive concise summary.
        created_at (datetime): Timestamp when the article was created in UTC.
    """

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=True)
    status = Column(
        String(50),
        default=ArticleStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    category = Column(String(255), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("url", name="uq_articles_url"),
    )