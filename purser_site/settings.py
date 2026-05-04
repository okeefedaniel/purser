"""
Purser — Financial Close, Reporting & Compliance
Django settings
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

import secrets as _secrets

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _secrets.token_hex(25)
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set in production')

DEMO_MODE = os.environ.get('DEMO_MODE', 'False').lower() in ('true', '1', 'yes')
DEMO_ROLES = ['purser_admin', 'agency_admin', 'purser_submitter', 'purser_reviewer', 'purser_compliance_officer', 'purser_readonly', 'external_submitter']

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Railway provides RAILWAY_PUBLIC_DOMAIN automatically
RAILWAY_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
    ALLOWED_HOSTS.append('.railway.app')

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_DOMAIN}')
CSRF_TRUSTED_ORIGINS = [o for o in CSRF_TRUSTED_ORIGINS if o]

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    # Keel (DockLabs shared platform)
    'keel.accounts',
    'keel.core',
    'keel.security',
    'keel.notifications',
    'keel.requests',
    'keel.periods',
    'keel.reporting',
    'keel.compliance',
    'keel.signatures',
    'keel.settings',
    # Third party
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    # Allauth (SSO / MFA)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.microsoft',
    'allauth.socialaccount.providers.openid_connect',  # Phase 2b: Keel as IdP
    'allauth.mfa',
    # Project apps
    'core.apps.CoreConfig',
    'purser.apps.PurserConfig',
]

SITE_ID = 1

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'keel.security.middleware.SecurityHeadersMiddleware',
    'keel.security.middleware.AdminIPAllowlistMiddleware',
    'keel.security.middleware.FailedLoginMonitor',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'keel.accounts.middleware.AutoOIDCLoginMiddleware',
    'keel.accounts.middleware.ProductAccessMiddleware',
    'keel.accounts.middleware.SessionFreshnessMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'keel.core.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'purser_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'keel.core.context_processors.site_context',
                'keel.core.context_processors.fleet_context',
                'keel.core.context_processors.breadcrumb_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'purser_site.wsgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}')
DATABASES = {
    'default': {},
}

import dj_database_url
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'keel_accounts.KeelUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Minimum password length (match all DockLabs products)
AUTH_PASSWORD_VALIDATORS[1]['OPTIONS'] = {'min_length': 10}

# ---------------------------------------------------------------------------
# Allauth (SSO / MFA)
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    # Username-or-email login (matches the shared LoginForm contract).
    'keel.accounts.backends.UsernameOrEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_ADAPTER = 'keel.core.sso.KeelAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'keel.core.sso.KeelSocialAccountAdapter'

SOCIALACCOUNT_LOGIN_ON_GET = True

_MSFT_TENANT = os.environ.get('MICROSOFT_TENANT_ID', 'common')
SOCIALACCOUNT_PROVIDERS = {
    'microsoft': {
        'APP': {
            'client_id': os.environ.get('MICROSOFT_CLIENT_ID', ''),
            'secret': os.environ.get('MICROSOFT_CLIENT_SECRET', ''),
        },
        'SCOPE': ['openid', 'email', 'profile', 'User.Read'],
        'AUTH_PARAMS': {'prompt': 'select_account'},
        'TENANT': _MSFT_TENANT,
    },
}

# ---------------------------------------------------------------------------
# Keel OIDC (Phase 2b) — Keel is the identity provider for the DockLabs suite
# ---------------------------------------------------------------------------
# When KEEL_OIDC_CLIENT_ID is set, this product federates authentication to
# Keel via standard OAuth2/OIDC. When unset, the product falls back to local
# Django auth (+ optional direct Microsoft SSO), so standalone deployments
# continue to work without any Keel dependency.
KEEL_OIDC_CLIENT_ID = os.environ.get('KEEL_OIDC_CLIENT_ID', '')
KEEL_OIDC_CLIENT_SECRET = os.environ.get('KEEL_OIDC_CLIENT_SECRET', '')
KEEL_OIDC_ISSUER = os.environ.get('KEEL_OIDC_ISSUER', 'https://keel.docklabs.ai')

if KEEL_OIDC_CLIENT_ID:
    SOCIALACCOUNT_PROVIDERS['openid_connect'] = {
        'APPS': [
            {
                'provider_id': 'keel',
                'name': 'Sign in with DockLabs',
                'client_id': KEEL_OIDC_CLIENT_ID,
                'secret': KEEL_OIDC_CLIENT_SECRET,
                'settings': {
                    'server_url': f'{KEEL_OIDC_ISSUER}/oauth/.well-known/openid-configuration',
                    'token_auth_method': 'client_secret_post',
                    'oauth_pkce_enabled': True,  # Keel requires PKCE
                    'scope': ['openid', 'email', 'profile', 'product_access', 'organization'],
                },
            },
        ],
    }

MFA_ADAPTER = 'allauth.mfa.adapter.DefaultMFAAdapter'
MFA_SUPPORTED_TYPES = ['totp', 'webauthn', 'recovery_codes']
MFA_TOTP_ISSUER = 'Purser'
MFA_PASSKEY_LOGIN_ENABLED = True

# ---------------------------------------------------------------------------
# Keel
# ---------------------------------------------------------------------------
KEEL_PRODUCT_CODE = 'purser'
from keel.core.fleet import FLEET as KEEL_FLEET_PRODUCTS  # noqa: E402,F401
KEEL_PRODUCT_NAME = 'Purser'
KEEL_PRODUCT_ICON = 'bi-safe2'
KEEL_PRODUCT_SUBTITLE = 'Financial Management'
KEEL_GATE_ACCESS = True
KEEL_AUDIT_LOG_MODEL = 'purser_core.AuditLog'
KEEL_NOTIFICATION_MODEL = 'purser_core.Notification'
KEEL_NOTIFICATION_PREFERENCE_MODEL = 'purser_core.NotificationPreference'
KEEL_NOTIFICATION_LOG_MODEL = 'purser_core.NotificationLog'
KEEL_API_KEY = os.environ.get('KEEL_API_KEY', '')
HELM_FEED_API_KEY = os.environ.get('HELM_FEED_API_KEY', '')
KEEL_API_URL = os.environ.get('KEEL_API_URL', 'https://keel.docklabs.ai')

# Manifest cross-product signing handoff — closeout signing flows.
# Optional — when unset, keel.signatures.client.is_available() returns
# False and the UI falls back to local-sign.
MANIFEST_URL = os.environ.get('MANIFEST_URL', '')
MANIFEST_API_TOKEN = os.environ.get('MANIFEST_API_TOKEN', '')
MANIFEST_WEBHOOK_SECRET = os.environ.get('MANIFEST_WEBHOOK_SECRET', '')

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Crispy forms
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Email — Resend HTTP API for transactional emails (Railway blocks outbound SMTP)
# ---------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'keel.notifications.backends.resend_backend.ResendEmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'DockLabs <info@docklabs.ai>')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
# 8-hour idle window. Combined with SESSION_SAVE_EVERY_REQUEST below, the
# cookie's expiry slides forward on every request — an active user is
# never logged out mid-session, but an abandoned tab on a shared/kiosk
# machine expires within a workday. Government finance data warrants a
# tighter window than the 30-day default a generic SaaS dashboard picks.
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ---------------------------------------------------------------------------
# Logging — surface errors to stdout for Railway
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ---------------------------------------------------------------------------
# Security (production)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    # Railway's proxy handles HTTP→HTTPS redirect; don't do it in Django
    # (breaks Railway's internal healthcheck which sends plain HTTP)
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Admin allowlist + trusted-proxy config (keel.security) ---
# KEEL_ADMIN_ALLOWED_IPS: list of CIDR / IPs allowed to hit /admin/.
#   Empty list = no-op (dev). Set via env on every Railway service in prod.
# KEEL_TRUSTED_PROXY_COUNT: number of trusted proxies between the client and
#   Django. Railway = 1. If 0, X-Forwarded-For is ignored (client spoof-safe).
KEEL_ADMIN_ALLOWED_IPS = [
    ip.strip() for ip in os.environ.get('KEEL_ADMIN_ALLOWED_IPS', '').split(',')
    if ip.strip()
]
KEEL_TRUSTED_PROXY_COUNT = int(os.environ.get('KEEL_TRUSTED_PROXY_COUNT', '1'))

# Content-Security-Policy (keel SecurityHeadersMiddleware)
KEEL_CSP_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self' https://keel.docklabs.ai https://demo-keel.docklabs.ai"
