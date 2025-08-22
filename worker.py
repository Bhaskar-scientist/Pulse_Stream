"""Celery worker configuration for PulseStream."""

from celery import Celery

from core.config import settings
from core.logging import configure_logging, get_logger

# Configure logging
configure_logging(settings.log_level, settings.log_format)
logger = get_logger("celery")

# Create Celery app
celery_app = Celery(
    "pulsestream",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "apps.processing.tasks",
        "apps.alerting.tasks",
        "apps.analytics.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes=settings.celery_task_routes,
    beat_schedule={
        # TODO: Add periodic tasks
        # "process-metrics": {
        #     "task": "apps.processing.tasks.process_metrics",
        #     "schedule": 60.0,  # Every minute
        # },
    },
)


# Task success callback
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info("Debug task executed", task_id=self.request.id)
    return f"Request: {self.request!r}"


if __name__ == "__main__":
    celery_app.start()
