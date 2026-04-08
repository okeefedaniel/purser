from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from keel.core.demo import demo_login_view
from keel.core.views import health_check, robots_txt, SuiteLogoutView

from core.forms import LoginForm
from purser.views import dashboard as purser_dashboard

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('demo-login/', demo_login_view, name='demo_login'),
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    # Canonical suite-wide post-login URL. Mounts the real Purser
    # dashboard view directly so the URL bar stays at /dashboard/.
    # The legacy /purser/ URL still works.
    path('dashboard/', purser_dashboard, name='dashboard_alias'),
    path('admin/', admin.site.urls),

    # Custom login/logout views using the shared keel LoginForm so the
    # input fields render with Bootstrap styling. Mounted before the
    # allauth include so they shadow allauth's bare LoginView.
    path('accounts/login/', LoginView.as_view(
        template_name='account/login.html',
        authentication_form=LoginForm,
    ), name='account_login'),
    path('accounts/logout/', SuiteLogoutView.as_view(), name='account_logout'),
    # Convenience named URL for the "Sign in with Microsoft" button
    path(
        'auth/sso/microsoft/',
        RedirectView.as_view(url='/accounts/microsoft/login/?process=login', query_string=False),
        name='microsoft_login',
    ),

    # Purser app
    path('purser/', include('purser.urls')),

    # Keel accounts
    path('keel/', include('keel.accounts.urls')),

    # Allauth (SSO + remaining account URLs)
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
