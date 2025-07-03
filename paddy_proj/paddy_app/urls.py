from django.urls import path
from .views import *

# API routes for paddy_app - legacy/shared functionality
# All UI routes have been moved to microservice apps
urlpatterns = [
    # Payment API endpoints that might be shared
    path('create-partial-payment/', create_partial_payment_order, name='create_partial_payment_order'),
    path('verify-partial-payment/', verify_partial_payment, name='verify_partial_payment'),
    
    # Admin subscription API endpoints
    path('create-admin-increase-order/', create_admin_user_increase_order, name='create_admin_user_increase_order'),
    path('verify-admin-increase-payment/', verify_admin_user_increase_payment, name='verify_admin_user_increase_payment'),
    
    # Cash payment API endpoints
    path('request-cash-payment/', request_cash_payment, name='request_cash_payment'),
    path('approve-cash-payment/<int:request_id>/', approve_cash_payment, name='approve_cash_payment'),
]