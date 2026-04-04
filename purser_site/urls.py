from allauth.account import views as allauth_views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from keel.core.demo import demo_login_view

urlpatterns = [
    path('demo-login/', demo_login_view, name='demo_login'),
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('admin/', admin.site.urls),

    # Auth — explicit login/logout with our template, before allauth catch-all
    path('accounts/login/', allauth_views.LoginView.as_view(
        template_name='account/login.html',
    ), name='account_login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='account_logout'),

    # Purser app
    path('purser/', include('purser.urls')),

    # Keel accounts
    path('keel/', include('keel.accounts.urls')),

    # Allauth (SSO + remaining account URLs)
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
