from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    # Admin dashboard and core views
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-subscription/', views.admin_add_subscription, name='admin_add_subscription'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('admin-place-order/', views.admin_place_order, name='admin_place_order'),
    path('customer-list/', views.customers_under_admin, name='admin_customer_list'),
    path('subscribers/', views.view_admin_subscribers, name='admin_subscribers'),
    path('subscription-payment/', views.admin_subscription_payment, name='admin_subscription_payment'),
    path('subscription-success/', views.admin_subscription_success, name='admin_subscription_success'),
    path('select-subscription-plan/', views.admin_select_subscription_plan, name='admin_select_subscription_plan'),
    path('upgrade-to-customer/', views.upgrade_to_customer, name='upgrade_to_customer'),
    path('view-admins/', views.view_admins, name='view_admins'),
    
    # Additional admin functionality
    path('create-customer/', views.create_customer, name='create_customer'),
    path('customer-onboard/', views.customer_onboard_view, name='customer_onboard'),
    path('notifications/', views.admin_notifications, name='admin_notifications'),
    path('create-admin-user-increase-order/', views.create_admin_user_increase_order, name='create_admin_user_increase_order'),
    path('verify-admin-user-increase-payment/', views.verify_admin_user_increase_payment, name='verify_admin_user_increase_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('upgrade-plan/', views.upgrade_plan, name='upgrade_plan'),
    path('upgrade-success/', views.upgrade_success, name='upgrade_success'),
]
