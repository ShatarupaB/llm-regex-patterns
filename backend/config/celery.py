import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

app = Celery("config")

# Load Django settings (serializers, task tracking, etc.)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Set broker AFTER config_from_object so it cannot be overwritten.
app.conf.broker_url = REDIS_URL
app.conf.result_backend = REDIS_URL

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
