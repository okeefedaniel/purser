#!/bin/bash
set -e

# Force-reinstall keel at runtime to dodge nixpacks/pip install caching.
# Without this, a stale `keel==0.8.0` from an earlier build silently
# shadows the pinned commit in requirements.txt and we ship old code.
# Once the version-bump-on-every-release pattern is established for
# all products, this can be removed.
echo "Re-resolving keel from requirements.txt..."
KEEL_LINE=$(grep -E '^keel @' requirements.txt || true)
if [ -n "$KEEL_LINE" ]; then
    pip install --upgrade --force-reinstall --no-deps "$KEEL_LINE" || true
fi

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
