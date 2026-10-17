from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator
from app.models.article import ArticleStatus


def normalize_status_val(v: Any) -> Any:
    if isinstance(v, str):
        mapping = {
            "pending": ArticleStatus.PENDING,
            "processing": ArticleStatus.PROCESSING,
            "completed": ArticleStatus.COMPLETED,
            "failed": ArticleStatus.FAILED,
        }
        return mapping.get(v.strip().lower(), v)
    return v


class ArticleBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255, description="Name of the company")
    title: str = Field(..., min_length=1, max_length=500, description="Title of the article")
    url: str = Field(..., min_length=1, max_length=1000, description="Unique article URL (valid HTTP/HTTPS)")
    content: Optional[str] = Field(None, description="Full article content")
    status: ArticleStatus = Field(default=ArticleStatus.PENDING, description="Current processing status")
    category: Optional[str] = Field(None, max_length=255, description="Category of the article")
    summary: Optional[str] = Field(None, description="Summary or excerpt of the article")

    @field_validator("company_name", "title")
    @classmethod
    def validate_non_blank_string(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field must not be empty or blank whitespace")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        cleaned = v.strip()
        TypeAdapter(HttpUrl).validate_python(cleaned)
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        return normalize_status_val(v)


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    url: Optional[str] = Field(None, min_length=1, max_length=1000)
    content: Optional[str] = None
    status: Optional[ArticleStatus] = None
    category: Optional[str] = Field(None, max_length=255)
    summary: Optional[str] = None

    @field_validator("company_name", "title")
    @classmethod
    def validate_non_blank_update(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Field must not be empty or blank whitespace")
            return cleaned
        return None

    @field_validator("url")
    @classmethod
    def validate_update_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            TypeAdapter(HttpUrl).validate_python(cleaned)
            return cleaned
        return None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        return normalize_status_val(v)


class ArticleResponse(BaseModel):
    id: int
    company_name: str
    title: str
    url: str
    content: Optional[str] = None
    status: ArticleStatus
    category: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        return normalize_status_val(v)

    model_config = ConfigDict(from_attributes=True)


class PaginatedArticleResponse(BaseModel):
    total: int = Field(..., ge=0, description="Total count of matching articles")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
    items: List[ArticleResponse] = Field(..., description="List of articles for the current page")
