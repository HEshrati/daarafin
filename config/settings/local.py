import os

os.environ.setdefault("DJANGO_SECRET_KEY", "local-only-insecure-key")
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web"]
