"""Celery worker and task queue initialization module.

Configures the Celery application with Redis as broker and backend,
enforcing JSON serialization, UTC timestamps, task execution tracking,
and configurable eager task execution.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "article_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.article_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)
