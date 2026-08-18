"""Django project configuration package (implemented in later tasks)."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
