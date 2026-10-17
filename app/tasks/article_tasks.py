"""Celery asynchronous tasks and core article processing logic.

Executes deterministic classification and summarization, manages article state transitions
(Pending -> Processing -> Completed/Failed), and handles automatic retries with exponential backoff.
"""

import logging
from typing import Any, Dict
from celery.exceptions import MaxRetriesExceededError

from app.core.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.article import Article, ArticleStatus
from app.services.classifier import ArticleClassifier
from app.services.summarizer import ArticleSummarizer

logger = logging.getLogger(__name__)


def process_article_sync(article_id: int) -> Dict[str, Any]:
    """Execute synchronous article classification and summarization workflow.

    1. Retrieves the article from the database.
    2. Updates status to 'Processing'.
    3. Runs deterministic classification on headline and body.
    4. Runs deterministic extractive summarization.
    5. Saves category and summary, updating status to 'Completed'.
    6. On unrecoverable error, updates status to 'Failed'.

    Args:
        article_id (int): ID of the article to process.

    Raises:
        Exception: Re-raises caught exceptions to trigger Celery retry mechanisms.

    Returns:
        Dict[str, Any]: Status summary dictionary with article details.
    """
    db = SyncSessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.warning(f"Article id {article_id} not found for processing.")
            return {"status": "not_found", "article_id": article_id}

        # 1. Update status to Processing
        article.status = ArticleStatus.PROCESSING.value
        db.commit()
        db.refresh(article)

        # 2. Perform deterministic classification
        category = ArticleClassifier.classify(
            title=article.title, content=article.content
        )

        # 3. Perform deterministic summarization
        summary = ArticleSummarizer.summarize(
            title=article.title, content=article.content
        )

        # 4. Save results and mark as Completed
        article.category = category
        article.summary = summary
        article.status = ArticleStatus.COMPLETED.value
        db.commit()
        db.refresh(article)

        logger.info(
            f"Successfully processed article {article_id}: Category='{category}', Status='{article.status}'"
        )
        return {
            "status": "success",
            "article_id": article_id,
            "category": category,
            "summary": summary,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Error processing article {article_id}: {exc}", exc_info=True)
        # Mark as Failed on unhandled error
        try:
            failed_article = db.query(Article).filter(Article.id == article_id).first()
            if failed_article:
                failed_article.status = ArticleStatus.FAILED.value
                db.commit()
        except Exception:
            db.rollback()
        raise exc
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.article_tasks.process_article_task",
    max_retries=3,
    default_retry_delay=5,
)
def process_article_task(self, article_id: int) -> Dict[str, Any]:
    """Celery task that asynchronously classifies and summarizes a news article.

    Implements automatic retries with exponential backoff on transient errors.

    Args:
        self: Bound Celery Task instance.
        article_id (int): Primary key ID of the article to process.

    Returns:
        Dict[str, Any]: Processing result metadata dictionary.
    """
    try:
        return process_article_sync(article_id=article_id)
    except Exception as exc:
        try:
            logger.warning(
                f"Retrying article processing for ID {article_id} (Attempt {self.request.retries + 1}/3)..."
            )
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for article {article_id}.")
            return {
                "status": "failed",
                "article_id": article_id,
                "error": str(exc),
            }
