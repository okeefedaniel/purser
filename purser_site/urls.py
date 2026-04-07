from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from keel.core.demo import demo_login_view
from keel.core.views import health_check, robots_txt

from core.forms import LoginForm

LANDING_CONTEXT = {
    'landing_stats': [
        {'value': 'Monthly', 'label': 'Close Cycle'},
        {'value': 'Variance', 'label': 'Analysis'},
        {'value': 'Compliance', 'label': 'Tracking'},
        {'value': 'Harbor', 'label': 'Integration'},
    ],
    'landing_features': [
        {'icon': 'bi-calendar-check', 'title': 'Monthly Close',
         'description': 'Run your fiscal close cycle with submission tracking, review queues, and automated reminder workflows.',
         'color': 'blue'},
        {'icon': 'bi-bar-chart', 'title': 'Variance Analysis',
         'description': 'Track budget vs. actual at every grant program level with drill-down to source transactions.',
         'color': 'teal'},
        {'icon': 'bi-clipboard-check', 'title': 'Compliance Tracking',
         'description': 'Manage federal and state compliance obligations with template-driven checklists and audit trails.',
         'color': 'yellow'},
    ],
    'landing_steps': [
        {'title': 'Configure Periods', 'description': 'Set up fiscal periods, grant programs, and compliance schedules.'},
        {'title': 'Track Submissions', 'description': 'Monitor monthly close packages from agency submitters.'},
        {'title': 'Review & Approve', 'description': 'Variance analysis flags exceptions for fiscal officer review.'},
        {'title': 'Close & Audit', 'description': 'Lock periods, generate reports, and maintain a full audit trail.'},
    ],
}

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('demo-login/', demo_login_view, name='demo_login'),
    path('', TemplateView.as_view(
        template_name='landing.html',
        extra_context=LANDING_CONTEXT,
    ), name='landing'),
    path('admin/', admin.site.urls),

    # Auth — explicit login/logout with our template, before allauth catch-all
    path('auth/login/', LoginView.as_view(
        template_name='account/login.html',
        authentication_form=LoginForm,
    ), name='account_login'),
    path('auth/logout/', LogoutView.as_view(), name='account_logout'),
    path(
        'auth/sso/microsoft/',
        RedirectView.as_view(url='/accounts/microsoft/login/?process=login', query_string=False),
        name='microsoft_login',
    ),

    path('purser/', include('purser.urls')),
    path('keel/', include('keel.accounts.urls')),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
