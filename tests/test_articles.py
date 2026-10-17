"""Automated unit and integration test suite for the News Article service.

Verifies:
- Service health endpoint
- Article creation, validations, and duplicate URL conflicts (409)
- Pagination, page boundaries, and X-Total-Count headers
- Company name and processing status filtering
- Single article retrieval and 404 errors
- Deterministic classification taxonomy accuracy across all categories
- Journalistic extractive summarization logic and fallbacks
- Full asynchronous processing pipeline and status transitions
- Manual task trigger endpoint (202 Accepted)
"""

import uuid
import pytest
from httpx import AsyncClient

from app.services.classifier import ArticleClassifier
from app.services.summarizer import ArticleSummarizer
from app.tasks.article_tasks import process_article_sync


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the /health endpoint returns HTTP 200 and healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_article_success(client: AsyncClient):
    """Test successful article creation returns HTTP 201 with populated metadata."""
    unique_slug = uuid.uuid4().hex[:8]
    payload = {
        "company_name": "Tech Corp",
        "title": f"The Future of AI {unique_slug}",
        "url": f"https://techcorp.example.com/articles/{unique_slug}",
        "content": "Full content of the article...",
        "status": "Pending",
        "category": "Technology",
        "summary": "Brief summary of tech trends.",
    }
    response = await client.post("/articles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == payload["company_name"]
    assert data["title"] == payload["title"]
    assert data["url"] == payload["url"]
    assert data["status"] == "Pending"
    assert data["category"] == "Technology"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_article_duplicate_url(client: AsyncClient):
    """Test creating an article with a duplicate URL raises HTTP 409 Conflict."""
    unique_slug = uuid.uuid4().hex[:8]
    payload = {
        "company_name": "Unique Media",
        "title": "Duplicate URL Article",
        "url": f"https://media.example.com/{unique_slug}",
        "content": "Some content",
        "status": "Pending",
    }
    # First creation should succeed
    res1 = await client.post("/articles", json=payload)
    assert res1.status_code == 201

    # Second creation with identical URL must return 409 Conflict
    res2 = await client.post("/articles", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_create_article_validation_errors(client: AsyncClient):
    """Test payload validation: missing fields, empty strings, invalid URLs, and invalid statuses."""
    # Missing required field company_name
    res_missing = await client.post(
        "/articles",
        json={"title": "Missing Company", "url": "https://example.com/valid-url"},
    )
    assert res_missing.status_code == 422

    # Empty string for company_name
    res_empty = await client.post(
        "/articles",
        json={"company_name": "   ", "title": "Valid Title", "url": "https://example.com/valid-url"},
    )
    assert res_empty.status_code == 422

    # Malformed URL
    res_invalid_url = await client.post(
        "/articles",
        json={"company_name": "Co", "title": "Title", "url": "not-a-valid-url"},
    )
    assert res_invalid_url.status_code == 422

    # Invalid status enum
    res_invalid_status = await client.post(
        "/articles",
        json={
            "company_name": "Co",
            "title": "Title",
            "url": "https://example.com/valid-enum",
            "status": "InvalidStatus",
        },
    )
    assert res_invalid_status.status_code == 422


@pytest.mark.asyncio
async def test_get_articles_pagination_and_headers(client: AsyncClient):
    """Test paginated listing returns correct pagination schema and X-Total-Count header."""
    response = await client.get("/articles?page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["limit"] == 5
    assert "x-total-count" in response.headers


@pytest.mark.asyncio
async def test_get_articles_filters(client: AsyncClient):
    """Test filtering articles by company_name substring and status enum."""
    unique_company = f"Company_{uuid.uuid4().hex[:6]}"
    unique_slug = uuid.uuid4().hex[:8]

    # Create an article with unique company and status Completed
    payload = {
        "company_name": unique_company,
        "title": "Filtered Article",
        "url": f"https://example.com/filter/{unique_slug}",
        "status": "Completed",
        "category": "Testing",
    }
    create_res = await client.post("/articles", json=payload)
    assert create_res.status_code == 201

    # Filter by company_name
    res_filter_company = await client.get(f"/articles?company_name={unique_company}")
    assert res_filter_company.status_code == 200
    company_data = res_filter_company.json()
    assert company_data["total"] >= 1
    assert all(unique_company.lower() in item["company_name"].lower() for item in company_data["items"])

    # Filter by status
    res_filter_status = await client.get(f"/articles?company_name={unique_company}&status=Completed")
    assert res_filter_status.status_code == 200
    status_data = res_filter_status.json()
    assert status_data["total"] >= 1
    assert all(item["status"] == "Completed" for item in status_data["items"])

    # Filter by status where none match
    res_filter_none = await client.get(f"/articles?company_name={unique_company}&status=Failed")
    assert res_filter_none.status_code == 200
    assert res_filter_none.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_article_by_id_and_not_found(client: AsyncClient):
    """Test retrieving article by ID and 404 response for missing IDs."""
    unique_slug = uuid.uuid4().hex[:8]
    create_res = await client.post(
        "/articles",
        json={
            "company_name": "FindMe Inc",
            "title": "Article To Find",
            "url": f"https://findme.example.com/{unique_slug}",
        },
    )
    assert create_res.status_code == 201
    article_id = create_res.json()["id"]

    # Valid ID lookup
    res_found = await client.get(f"/articles/{article_id}")
    assert res_found.status_code == 200
    assert res_found.json()["id"] == article_id

    # Non-existent ID lookup
    res_not_found = await client.get("/articles/999999999")
    assert res_not_found.status_code == 404
    assert "not found" in res_not_found.json()["detail"].lower()


# --- Classification & Summarization Tests ---

def test_deterministic_classifier_example_input():
    """Verify classifier produces 'Automotive' for the example specification."""
    title = "Company announces investment in a new electric vehicle plant"
    content = "The company will invest $2 billion to expand vehicle production and create jobs."
    category = ArticleClassifier.classify(title=title, content=content)
    assert category == "Automotive"


def test_deterministic_classifier_categories():
    """Verify classification accuracy across multiple distinct domain categories."""
    # Technology
    assert ArticleClassifier.classify("Tech Giant Unveils New Artificial Intelligence Cloud Platform") == "Technology"
    # Healthcare
    assert ArticleClassifier.classify("Biotech firm begins clinical trials for new vaccine candidate") == "Healthcare"
    # Finance
    assert ArticleClassifier.classify("Central Banking Institution Reports Record Fintech Growth and Dividends") == "Finance"
    # Energy
    assert ArticleClassifier.classify("Massive Solar and Wind Renewable Energy Farm Launches Operations") == "Energy"
    # Business Fallback
    assert ArticleClassifier.classify("Corporate Quarterly Earnings and Acquisition Update") == "Business"


def test_deterministic_summarizer():
    """Verify extractive lead summarization and fallback when content is empty."""
    title = "Company announces investment in a new electric vehicle plant"
    content = "The company will invest $2 billion to expand vehicle production and create jobs. Operations will commence in 2027."
    summary = ArticleSummarizer.summarize(title=title, content=content)
    assert "$2 billion" in summary
    assert "vehicle production" in summary

    # Empty content fallback
    empty_summary = ArticleSummarizer.summarize(title=title, content="")
    assert empty_summary == title


@pytest.mark.asyncio
async def test_async_article_processing_pipeline(client: AsyncClient):
    """Verify the full asynchronous processing lifecycle from Pending to Completed."""
    unique_slug = uuid.uuid4().hex[:8]
    payload = {
        "company_name": "NextGen Motors",
        "title": "Company announces investment in a new electric vehicle plant",
        "url": f"https://nextgen.example.com/{unique_slug}",
        "content": "The company will invest $2 billion to expand vehicle production and create jobs.",
    }
    # Create article initially in Pending status
    res = await client.post("/articles", json=payload)
    assert res.status_code == 201
    article_id = res.json()["id"]

    # Process article synchronously using the processing core
    result = process_article_sync(article_id=article_id)
    assert result["status"] == "success"
    assert result["category"] == "Automotive"
    assert "$2 billion" in result["summary"]

    # Retrieve article and verify persistence
    get_res = await client.get(f"/articles/{article_id}")
    assert get_res.status_code == 200
    article_data = get_res.json()
    assert article_data["status"] == "Completed"
    assert article_data["category"] == "Automotive"
    assert "$2 billion" in article_data["summary"]


@pytest.mark.asyncio
async def test_trigger_process_endpoint(client: AsyncClient):
    """Verify manual task queuing via POST /articles/{id}/process returns HTTP 202."""
    unique_slug = uuid.uuid4().hex[:8]
    create_res = await client.post(
        "/articles",
        json={
            "company_name": "AI Innovations",
            "title": "Cloud Computing and Artificial Intelligence Software Launch",
            "url": f"https://ai.example.com/{unique_slug}",
            "content": "The firm launched a breakthrough machine learning SaaS tool today.",
        },
    )
    assert create_res.status_code == 201
    article_id = create_res.json()["id"]

    # Trigger processing endpoint
    trigger_res = await client.post(f"/articles/{article_id}/process")
    assert trigger_res.status_code == 202
    assert trigger_res.json()["message"] == "Article processing task queued"