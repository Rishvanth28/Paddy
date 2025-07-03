from django.urls import path
from . import views

app_name = 'notifications_app'

urlpatterns = [
    # Customer notifications
    path('customer/', views.customer_notifications, name='customer_notifications'),
    
    # Admin notifications
    path('admin/', views.admin_notifications, name='admin_notifications'),
    # Superadmin notifications
    path('superadmin/', views.superadmin_notifications, name='superadmin_notifications'),
    # AJAX endpoints for notification management
    path('mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('delete/', views.delete_notifications, name='delete_notifications'),
]
