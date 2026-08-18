#!/bin/sh
set -eu
if [ "${DJANGO_SETTINGS_MODULE:-}" = "config.settings.local" ] && [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi
exec "$@"
