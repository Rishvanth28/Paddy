from django.urls import path
from . import views

app_name = 'superadmin_app'

urlpatterns = [
    # Superadmin core views  
    path('dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('subscription/', views.superadmin_subscription, name='superadmin_subscription'),
    path('subscription-review/', views.superadmin_subscription_review, name='superadmin_subscription_review'),
    path('orders/', views.super_admin_orders, name='super_admin_orders'),
    path('notifications/', views.superadmin_notifications, name='superadmin_notifications'),
    
    # Admin management functionality
    path('view-admins/', views.view_admins, name='view_admins'),
    path('view-customers/<int:admin_id>/', views.view_customers_under_admin, name='admin_customers'),
    path('customer-subscribers/', views.view_customer_subscribers, name='customer_subscribers'),
    path('delete-admin/<int:admin_id>/', views.delete_admin, name='delete_admin'),
    path('delete-customer/<str:customer_id>/', views.delete_customer, name='delete_customer'),

    # Place Order functionality
    path('place-order/', views.place_order, name='place_order'),
]
