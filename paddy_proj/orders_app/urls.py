from django.urls import path
from . import views

app_name = 'orders_app'

urlpatterns = [
    # Customer Orders URLs
    path('customer-orders/', views.customer_orders, name='customer_orders'),
    path('customer-orders/payment/', views.payment, name='payment'),
    path('customer-orders/delivery/', views.customer_delivery_validation, name='delivery'),
    
    # Admin Orders URLs
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    
    # Superadmin Orders URLs
    path('super-admin-orders/', views.super_admin_orders, name='super_admin_orders'),
    
    # Payment URLs
    path('create-partial-payment-order/', views.create_partial_payment_order, name='create_partial_payment_order'),
    path('verify-partial-payment/', views.verify_partial_payment, name='verify_partial_payment'),
    path('request-cash-payment/', views.request_cash_payment, name='request_cash_payment'),
    path('approve-cash-payment/<int:request_id>/', views.approve_cash_payment, name='approve_cash_payment'),
    
    # Order Placement URLs
    path('place-order/', views.place_order, name='place_order'),
    path('admin-place-order/', views.place_order, name='admin_place_order'),
]
