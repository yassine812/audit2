"""Celery application configuration for audit2 project."""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

app = Celery("audit2")

# Read config from Django settings with CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()

# Fallback to solo pool to avoid multiprocessing issues on some platforms
app.conf.update(
    worker_pool="solo",
    task_track_started=True,
)
