from django.urls import path
from . import views

app_name = 'orders_app'

urlpatterns = [
    # Customer Orders URLs
    path('customer-orders/', views.customer_orders, name='customer_orders'),
    path('customer-orders/delivery/', views.customer_delivery_validation, name='delivery'),
    
    # Admin Orders URLs
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    
    # Superadmin Orders URLs
    path('super-admin-orders/', views.super_admin_orders, name='super_admin_orders'),
    
    # Order Placement URLs
    path('place-order/', views.place_order, name='place_order'),
    path('admin-place-order/', views.place_order, name='admin_place_order'),
    
    # API Endpoints
    path('api/get-customer-by-phone/', views.get_customer_by_phone, name='get_customer_by_phone'),
]
