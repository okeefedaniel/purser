#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Purser..."
exec gunicorn purser_site.wsgi --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120
