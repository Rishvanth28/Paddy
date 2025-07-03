from django.urls import path
from . import views

app_name = 'customer_app'

urlpatterns = [
    # Customer dashboard and core views
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('orders/', views.customer_orders, name='customer_orders'),
    path('onboard/', views.customer_onboard, name='customer_onboard'),
    path('subscribers/', views.customer_subscribers, name='customer_subscribers'),
    path('subscription-payment/', views.customer_subscription_payment, name='customer_subscription_payment'),
    path('select-subscription-plan/', views.customer_select_subscription_plan, name='customer_select_subscription_plan'),
    path('customers_list/', views.customers_list, name='customers_list'),
    path('upgrade-to-admin/', views.upgrade_to_admin, name='upgrade_to_admin'),
    
    
    
    # Additional customer functionality
    path('delivery/', views.customer_delivery_validation, name='delivery'),
    path('payment/', views.payment, name='payment'),
    path('notifications/', views.customer_notifications, name='customer_notifications'),
    path('payment-success/', views.customer_payment_success, name='customer_payment_success'),
    path('create-partial-payment-order/', views.create_partial_payment_order, name='create_partial_payment_order'),
    path('verify-partial-payment/', views.verify_partial_payment, name='verify_partial_payment'),
]
