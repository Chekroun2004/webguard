from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "webguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "watchdog-stuck-scans": {
        "task": "watchdog_stuck_scans",
        "schedule": 300.0,  # every 5 minutes
    },
    "run-due-scheduled-scans": {
        "task": "run_due_scheduled_scans",
        "schedule": 60.0,  # every minute
    },
}
