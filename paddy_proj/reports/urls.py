from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Reports URLs
    path('admin/', views.admin_reports, name='admin_reports'),
    path('superadmin/', views.superadmin_reports, name='superadmin_reports'),
]
