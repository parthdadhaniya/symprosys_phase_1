# News Article Management, Classification & Summarization Service

A high-performance, asynchronous backend service built with **FastAPI**, **PostgreSQL**, **SQLAlchemy (Async + Sync)**, and **Celery**. The service ingests news articles for companies, enforces data integrity (such as unique article URLs), classifies each article into deterministic business categories, generates concise extractive summaries, and processes workloads asynchronously with built-in retry and fallback mechanisms.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Architecture & Design](#architecture--design)
3. [Technology Stack](#technology-stack)
4. [Project Directory Structure](#project-directory-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Environment Configuration (`.env`)](#environment-configuration-env)
8. [Running the Application](#running-the-application)
   - [Running the FastAPI Server](#1-running-the-fastapi-server)
   - [Running the Celery Worker](#2-running-the-celery-worker)
9. [API Endpoints & Usage](#api-endpoints--usage)
   - [Interactive Swagger & ReDoc](#interactive-documentation)
   - [Endpoint Reference](#endpoint-reference)
   - [Example: Complete Workflow](#example-complete-workflow)
10. [Deterministic Classification & Summarization](#deterministic-classification--summarization)
11. [Reliability & Error Handling](#reliability--error-handling)
12. [Running the Test Suite](#running-the-test-suite)

---

## Key Features

- **Article CRUD Operations**: Create, read, list, update, and delete company news articles.
- **Strict Data Integrity**:
  - Unique database constraints on article URLs to prevent duplicate records.
  - Comprehensive Pydantic v2 validation (disallowing blank strings, enforcing valid HTTP/HTTPS URLs, validating enum states).
- **Asynchronous Task Processing**:
  - Celery worker executes article classification and summarization in the background.
  - Lifecycle state management: `Pending` -> `Processing` -> `Completed` (or `Failed`).
  - Automatic exponential backoff retries for transient database issues.
  - Graceful fallback: If Redis or Celery broker is temporarily offline, tasks safely execute via FastAPI's native `BackgroundTasks`.
- **Deterministic Classification**:
  - Weighted keyword taxonomy categorizing articles into **Automotive**, **Technology**, **Healthcare**, **Finance**, **Energy**, or **Business**.
  - Title matches are weighted 2.5x higher than body content matches.
  - No external ML model or LLM dependency required, ensuring fast, repeatable, and cost-effective execution.
- **Deterministic Extractive Summarizer**:
  - Journalistic lead-sentence extraction with statistical weighting for financial metrics, investments, numerical indicators, and key operational statements.
- **Pagination & Filtering**:
  - Pagination with `page`, `limit`, and optional `skip` offset.
  - Metadata in response (`total`, `page`, `limit`, `total_pages`, `items`) plus standard `X-Total-Count` HTTP header.
  - Optional filters for `company_name` (case-insensitive substring) and `status` (`Pending`, `Processing`, `Completed`, `Failed`).

---

## Architecture & Design

```
                     +----------------------------+
                     |        Client / UI         |
                     +--------------+-------------+
                                    | HTTP Requests (REST)
                                    v
                     +----------------------------+
                     |    FastAPI Application     |
                     |  (/articles, /api/v1/...)  |
                     +--------------+-------------+
                                    |
          +-------------------------+-------------------------+
          | Writes / Reads                                    | Enqueues Task
          v                                                   v
+-------------------+                               +--------------------+
|    PostgreSQL     |                               |   Redis Broker     |
| (articles table)  |                               +---------+----------+
+---------+---------+                                         |
          ^                                                   v
          | Reads / Updates status & summary        +--------------------+
          +-----------------------------------------|   Celery Worker    |
                                                    | (Async Classifier  |
                                                    |  & Summarizer)     |
                                                    +--------------------+
```

---

## Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (0.115+)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Data Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
- **Database & ORM**: PostgreSQL with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
  - `asyncpg` for non-blocking async endpoint queries
  - `psycopg2-binary` for Celery worker sync sessions
- **Background Worker & Broker**: [Celery](https://docs.celeryq.dev/) & [Redis](https://redis.io/)
- **Test Suite**: [pytest](https://docs.pytest.org/) & `pytest-asyncio` with `httpx`

---

## Project Directory Structure

```text
simprosys_test/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, CORS & route configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # V1 route aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── articles.py     # Article REST endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings (.env loader)
│   │   ├── database.py             # Async & sync engine/session factories
│   │   └── celery_app.py           # Celery application & configuration
│   ├── crud/
│   │   ├── __init__.py
│   │   └── article.py              # Database queries, pagination, filters
│   ├── models/
│   │   ├── __init__.py
│   │   ├── article.py              # SQLAlchemy Article table & ArticleStatus enum
│   │   └── models.py               # Re-exports for convenient imports
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── article.py              # Pydantic schemas (Create, Update, Response, Paginated)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── article.py              # Business logic & task dispatching
│   │   ├── classifier.py           # Deterministic category classification engine
│   │   └── summarizer.py           # Deterministic extractive summarization engine
│   └── tasks/
│       ├── __init__.py
│       └── article_tasks.py        # Celery background tasks & sync processor
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Async test fixtures, NullPool engine, test DB
│   └── test_articles.py            # Comprehensive unit & integration tests
├── .env.example                    # Template environment variables
├── .env                            # Active environment configuration
├── main.py                         # Root entrypoint for uvicorn
├── pytest.ini                      # Pytest and pytest-asyncio settings
├── requirements.txt                # Python package dependencies
└── README.md                       # Complete documentation
```

---

## Prerequisites

Before starting, ensure you have installed:
- **Python 3.10+** (tested on Python 3.12, 3.13, 3.14)
- **PostgreSQL 14+** running locally or accessible remotely
- **Redis 5+** (optional; required if running standalone Celery workers)

---

## Installation & Setup

### 1. Clone or Open the Project
```bash
cd "c:\My Projects\simprosys_test"
```

### 2. Create and Activate a Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux (Bash)**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## Environment Configuration (`.env`)

Create a `.env` file in the root directory (you can copy `.env.example`):

```bash
cp .env.example .env
```

Ensure your `.env` contains valid credentials for PostgreSQL and Redis:

```ini
# Application Configuration
APP_NAME="Article Management & Summarization API"
ENVIRONMENT="development"
DEBUG=True
PORT=8000
HOST="127.0.0.1"

# Database Configuration (PostgreSQL)
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=simprosys_test

# Async Database URL (FastAPI endpoints)
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Sync Database URL (Celery worker)
SYNC_DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis & Celery Broker Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}/0
CELERY_BROKER_URL=redis://${REDIS_HOST}:${REDIS_PORT}/0
CELERY_RESULT_BACKEND=redis://${REDIS_HOST}:${REDIS_PORT}/0
CELERY_TASK_ALWAYS_EAGER=False
```

> **Note on Database Setup**: The tables (`articles`) are automatically created when the FastAPI application starts up via its lifespan event (`Base.metadata.create_all`). No manual migration script is mandatory to get started.

---

## Running the Application

### 1. Running the FastAPI Server

You can run the web server using either of the following commands:

Using Uvicorn with auto-reload:
```bash
uvicorn main:app --reload
```
or directly via Python:
```bash
python main.py
```

The application will be live at:
- **Base URL**: `http://127.0.0.1:8000`
- **Health Check**: `http://127.0.0.1:8000/health`

### 2. Running the Celery Worker

To process tasks asynchronously with a dedicated worker process:

- **Windows** (using the `solo` pool for Windows compatibility):
  ```bash
  celery -A app.core.celery_app.celery_app worker --loglevel=info -P solo
  ```
- **Linux / macOS**:
  ```bash
  celery -A app.core.celery_app.celery_app worker --loglevel=info
  ```

> **Fallback Note**: If you do not have Redis running locally, the application automatically catches the broker connection exception and executes the classification and summarization asynchronously using FastAPI's built-in `BackgroundTasks`.

---

## API Endpoints & Usage

### Interactive Documentation
Once the server is running, open your browser:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Both `/articles` and `/api/v1/articles` route prefixes are supported.

### Endpoint Reference

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/articles` | Create an article and queue background processing | `201 Created` |
| `GET` | `/articles` | List articles with pagination & filters (`company_name`, `status`) | `200 OK` |
| `GET` | `/articles/{id}` | Get an article by ID | `200 OK` / `404` |
| `PUT` | `/articles/{id}` | Update article details | `200 OK` / `404` / `409` |
| `DELETE` | `/articles/{id}` | Delete an article | `204 No Content` / `404` |
| `POST` | `/articles/{id}/process` | Manually trigger or retry classification & summarization | `202 Accepted` |
| `GET` | `/health` | Health check endpoint | `200 OK` |

---

### Example: Complete Workflow

#### 1. Create an Article (`POST /articles`)

**Request**:
```http
POST /articles HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "company_name": "NextGen Motors",
  "title": "Company announces investment in a new electric vehicle plant",
  "url": "https://news.example.com/nextgen-ev-plant",
  "content": "The company will invest $2 billion to expand vehicle production and create jobs. Operations are scheduled to begin next year."
}
```

**Response (`201 Created`)**:
```json
{
  "id": 1,
  "company_name": "NextGen Motors",
  "title": "Company announces investment in a new electric vehicle plant",
  "url": "https://news.example.com/nextgen-ev-plant",
  "content": "The company will invest $2 billion to expand vehicle production and create jobs. Operations are scheduled to begin next year.",
  "status": "Pending",
  "category": null,
  "summary": null,
  "created_at": "2026-10-17T15:30:00.000000"
}
```

#### 2. Background Processing
The worker picks up the task, transitioning the article:
1. `status` becomes `Processing`.
2. Classifier detects `Automotive` (keywords: *electric vehicle*, *vehicle plant*, *vehicle production*).
3. Summarizer extracts the lead sentence containing financial figures:
   `"The company will invest $2 billion to expand vehicle production and create jobs."`
4. `status` is updated to `Completed`.

#### 3. Fetch Processed Article (`GET /articles/1`)

**Response (`200 OK`)**:
```json
{
  "id": 1,
  "company_name": "NextGen Motors",
  "title": "Company announces investment in a new electric vehicle plant",
  "url": "https://news.example.com/nextgen-ev-plant",
  "content": "The company will invest $2 billion to expand vehicle production and create jobs. Operations are scheduled to begin next year.",
  "status": "Completed",
  "category": "Automotive",
  "summary": "The company will invest $2 billion to expand vehicle production and create jobs.",
  "created_at": "2026-10-17T15:30:00.000000"
}
```

#### 4. List Articles with Pagination & Filters (`GET /articles`)

**Query Parameters**:
- `page`: Page number (default: `1`, minimum: `1`)
- `limit`: Items per page (default: `10`, maximum: `100`)
- `company_name`: Case-insensitive substring match (e.g. `NextGen`)
- `status`: One of `Pending`, `Processing`, `Completed`, `Failed`

**Example Request**:
```http
GET /articles?page=1&limit=5&company_name=NextGen&status=Completed HTTP/1.1
Host: 127.0.0.1:8000
```

**Response (`200 OK`)**:
```json
{
  "total": 1,
  "page": 1,
  "limit": 5,
  "total_pages": 1,
  "items": [
    {
      "id": 1,
      "company_name": "NextGen Motors",
      "title": "Company announces investment in a new electric vehicle plant",
      "url": "https://news.example.com/nextgen-ev-plant",
      "content": "The company will invest $2 billion to expand vehicle production and create jobs. Operations are scheduled to begin next year.",
      "status": "Completed",
      "category": "Automotive",
      "summary": "The company will invest $2 billion to expand vehicle production and create jobs.",
      "created_at": "2026-10-17T15:30:00.000000"
    }
  ]
}
```
*Response includes header:* `X-Total-Count: 1`

#### 5. Duplicate Prevention (`POST /articles` with existing URL)

Attempting to submit the same URL returns `409 Conflict`:
```json
{
  "detail": "Article with URL 'https://news.example.com/nextgen-ev-plant' already exists."
}
```

---

## Deterministic Classification & Summarization

### Classification Taxonomy (`app/services/classifier.py`)
Articles are categorized using weighted keyword matching without requiring external LLM API calls:

| Category | Typical Keywords | Weighting Rule |
| :--- | :--- | :--- |
| **Automotive** | electric vehicle, ev, vehicle production, vehicle plant, car, battery plant | Title: 2.5x, Content: 1.0x |
| **Technology** | artificial intelligence, ai, software, cloud, semiconductor, chips, saas | Title: 2.5x, Content: 1.0x |
| **Healthcare** | healthcare, pharmaceutical, biotech, clinical trial, vaccine, hospital | Title: 2.5x, Content: 1.0x |
| **Finance** | banking, fintech, stock, shares, dividend, cryptocurrency, ipo | Title: 2.5x, Content: 1.0x |
| **Energy** | renewable energy, solar, wind power, clean energy, pipeline, nuclear | Title: 2.5x, Content: 1.0x |
| **Business** | investment, acquisition, merger, revenue, profit, corporate, expansion | Default / Fallback |

### Extractive Summarizer (`app/services/summarizer.py`)
- Employs journalistic *inverted pyramid* scoring: lead statements are given highest priority.
- Boosts sentences containing financial metrics (`$2 billion`, percentages, currency signs) and corporate actions (*invest*, *expand*, *launch*).
- Limits maximum length to 350 characters and gracefully handles empty content by falling back to the article title.

---

## Reliability & Error Handling

- **Database-Level Protection**: An explicit `UniqueConstraint("url", name="uq_articles_url")` prevents duplicate records at the database level.
- **Pre-flight & Concurrency Conflict Handling**: Endpoints perform pre-flight checks and catch `IntegrityError` to return clean `409 Conflict` errors instead of 500 crashes.
- **Input Validation**: Pydantic models disallow whitespace-only strings and validate HTTP/HTTPS schemes, returning structured `422 Unprocessable Entity` details.
- **Celery Fault Tolerance**:
  - `max_retries=3` with exponential backoff (`5 * (2 ** retries)`) for transient connection errors.
  - On unrecoverable failure, the article's state is committed as `Failed`.
- **Worker Availability Fallback**: If Redis is not running in local development, tasks are queued seamlessly into FastAPI's in-process `BackgroundTasks`.

---

## Running the Test Suite

The test suite covers endpoints, request validation, URL uniqueness, pagination, filtering, classifier accuracy, extractive summarizer, and the Celery processing pipeline.

Run all tests:
```bash
pytest -v
```

Expected output:
```text
tests/test_articles.py::test_health_check PASSED                         [  8%]
tests/test_articles.py::test_create_article_success PASSED               [ 16%]
tests/test_articles.py::test_create_article_duplicate_url PASSED         [ 25%]
tests/test_articles.py::test_create_article_validation_errors PASSED     [ 33%]
tests/test_articles.py::test_get_articles_pagination_and_headers PASSED  [ 41%]
tests/test_articles.py::test_get_articles_filters PASSED                 [ 50%]
tests/test_articles.py::test_get_article_by_id_and_not_found PASSED      [ 58%]
tests/test_articles.py::test_deterministic_classifier_example_input PASSED [ 66%]
tests/test_articles.py::test_deterministic_classifier_categories PASSED  [ 75%]
tests/test_articles.py::test_deterministic_summarizer PASSED             [ 83%]
tests/test_articles.py::test_async_article_processing_pipeline PASSED    [ 91%]
tests/test_articles.py::test_trigger_process_endpoint PASSED             [100%]

============================= 12 passed in ~6s =============================
```

