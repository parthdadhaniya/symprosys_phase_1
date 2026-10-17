"""Celery tasks module."""
from app.tasks.article_tasks import process_article_task

__all__ = ["process_article_task"]

