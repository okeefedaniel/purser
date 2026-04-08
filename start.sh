#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Configuring Site object..."
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purser_site.settings')
django.setup()
from django.contrib.sites.models import Site
domain = os.environ.get('SITE_DOMAIN', 'purser.docklabs.ai')
site, created = Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': 'Purser'})
print(f'  Site {\"created\" if created else \"updated\"}: {site.domain}')
"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Purser..."
exec gunicorn purser_site.wsgi --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120
