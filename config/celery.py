import os

from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("darafin")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_queues = tuple(
    Queue(name, Exchange(name, type="direct"), routing_key=name)
    for name in ("financial-critical", "integrations", "documents", "notifications")
)
app.conf.task_default_queue = "integrations"
app.conf.beat_schedule = {}
app.autodiscover_tasks()


@app.task(name="darafin.ping")
def ping() -> str:
    return "pong"
