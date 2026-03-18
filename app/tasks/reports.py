"""Report generation Celery tasks."""

from celery import shared_task

from app.tasks.celery_app import celery_app


@celery_app.task(name="reports.generate_scheduled_report")
def generate_scheduled_report(report_id: int) -> dict:
    """Generate and distribute a scheduled report."""
    # TODO: Implement report generation logic
    return {"status": "pending", "report_id": report_id}


@celery_app.task(name="reports.daily_digest")
def daily_digest() -> dict:
    """Generate daily digest of all metrics."""
    # TODO: Implement daily digest logic
    return {"status": "pending"}
