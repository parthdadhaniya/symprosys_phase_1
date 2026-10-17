from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from app.core.database import Base


class ArticleStatus(str, enum.Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Article(Base):
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
