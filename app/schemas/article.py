"""Pydantic schemas and DTOs for Article request validation and API responses.

Enforces strict validations:
- Non-empty, non-whitespace strings for mandatory text fields.
- Valid HTTP/HTTPS URI scheme for article URLs.
- Case-insensitive status normalization to ArticleStatus enum values.
- Comprehensive response schemas including pagination envelopes.
"""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator
from app.models.article import ArticleStatus


def normalize_status_val(v: Any) -> Any:
    """Normalize string input into an ArticleStatus enum value (case-insensitive).

    Args:
        v (Any): Raw status input from payload or database.

    Returns:
        ArticleStatus or Any: Corresponding enum member if recognized, otherwise original value.
    """
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
    """Base schema defining common attributes across Article payloads."""

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
        """Ensure string fields contain non-whitespace characters."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field must not be empty or blank whitespace")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the URL string complies with standard HTTP/HTTPS URL format."""
        cleaned = v.strip()
        TypeAdapter(HttpUrl).validate_python(cleaned)
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and return None if string is empty."""
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        """Normalize status string to ArticleStatus enum."""
        return normalize_status_val(v)


class ArticleCreate(ArticleBase):
    """Schema for article creation requests."""

    pass


class ArticleUpdate(BaseModel):
    """Schema for updating an existing article. All fields are optional."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Article title")
    url: Optional[str] = Field(None, min_length=1, max_length=1000, description="Article URL")
    content: Optional[str] = Field(None, description="Article body content")
    status: Optional[ArticleStatus] = Field(None, description="Processing status")
    category: Optional[str] = Field(None, max_length=255, description="Category")
    summary: Optional[str] = Field(None, description="Article summary")

    @field_validator("company_name", "title")
    @classmethod
    def validate_non_blank_update(cls, v: Optional[str]) -> Optional[str]:
        """Disallow updating string fields to whitespace-only values."""
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Field must not be empty or blank whitespace")
            return cleaned
        return None

    @field_validator("url")
    @classmethod
    def validate_update_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided in update payload."""
        if v is not None:
            cleaned = v.strip()
            TypeAdapter(HttpUrl).validate_python(cleaned)
            return cleaned
        return None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        """Normalize status string to ArticleStatus enum."""
        return normalize_status_val(v)


class ArticleResponse(BaseModel):
    """Schema returned for a single article representation."""

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
        """Normalize status value for response serialization."""
        return normalize_status_val(v)

    model_config = ConfigDict(from_attributes=True)


class PaginatedArticleResponse(BaseModel):
    """Schema for paginated article list responses."""

    total: int = Field(..., ge=0, description="Total count of matching articles")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
    items: List[ArticleResponse] = Field(..., description="List of articles for the current page")