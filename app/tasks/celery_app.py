"""Celery application configuration."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "skynet",
    broker_url=settings.celery.broker_url,
    result_backend=settings.celery.result_backend,
    include=[
        "app.tasks.reports",
        "app.tasks.agents",
    ],
)

celery_app.conf.update(
    serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

celery_app.conf.beat_schedule = {}
