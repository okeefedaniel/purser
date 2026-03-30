from django.urls import path

from . import views

app_name = 'purser'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Submissions
    path('submit/<str:program_code>/<uuid:period_id>/',
         views.submission_form, name='submission_form'),
    path('save-line/<uuid:value_id>/',
         views.save_line_value, name='save_line_value'),
    path('transition/<uuid:submission_id>/<str:target_status>/',
         views.transition_submission, name='transition_submission'),

    # Review
    path('review/', views.review_queue, name='review_queue'),
    path('review/<uuid:submission_id>/', views.review_detail, name='review_detail'),

    # Compliance
    path('compliance/', views.compliance_dashboard, name='compliance_dashboard'),
    path('compliance/<uuid:item_id>/', views.compliance_detail, name='compliance_detail'),

    # External Portal
    path('portal/', views.portal_dashboard, name='portal_dashboard'),

    # Close Package
    path('close/<uuid:period_id>/', views.close_package, name='close_package'),

    # Program Admin
    path('admin/programs/', views.program_list, name='program_list'),
    path('admin/programs/new/', views.program_form, name='program_create'),
    path('admin/programs/<uuid:program_id>/', views.program_form, name='program_edit'),
]
