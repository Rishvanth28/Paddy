from django.urls import path
from . import views

app_name = 'payment_app'

urlpatterns = [
    # Order Booking Fee Payment URLs
    path('order-booking-payment/', views.order_booking_payment, name='order_booking_payment'),
    
    # Order Payment URLs
    path('invoice/', views.payment, name='payment'),
    
    # Partial Payment URLs
    path('create-partial-payment-order/', views.create_partial_payment_order, name='create_partial_payment_order'),
    path('verify-partial-payment/', views.verify_partial_payment, name='verify_partial_payment'),
    path('debug-payment-verification/', views.debug_payment_verification, name='debug_payment_verification'),
    
    # Cash Payment URLs
    path('request-cash-payment/', views.request_cash_payment, name='request_cash_payment'),
    path('approve-cash-payment/<int:request_id>/', views.approve_cash_payment, name='approve_cash_payment'),
    
    # Subscription Payment URLs
    # Removed old admin-subscription-payment - use admin-product-subscription instead
    path('admin-product-subscription/', views.admin_product_subscription, name='admin_product_subscription'),
    path('verify-product-subscription-payment/', views.verify_product_subscription_payment, name='verify_product_subscription_payment'),
    path('customer-subscription-payment/', views.customer_subscription_payment, name='customer_subscription_payment'),
    path('admin-payment-success/', views.payment_success, name='payment_success'),
    path('customer-payment-success/', views.customer_payment_success, name='customer_payment_success'),
    path('verify-admin-user-increase-payment/', views.verify_admin_user_increase_payment, name='verify_admin_user_increase_payment'),
    path('create-admin-user-increase-order/', views.create_admin_user_increase_order, name='create_admin_user_increase_order'),
]
