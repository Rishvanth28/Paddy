from django.urls import path
from django.shortcuts import redirect
from .views import *


urlpatterns = [
    path("", lambda request: redirect('/login/'), name="home"),  # Redirect root to login
    
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("customer-dashboard/", customer_dashboard, name="customer_dashboard"),

    path("admin-add-subscription/", admin_add_subscription, name="admin_add_subscription"),
    path("upgrade-plan/", upgrade_plan, name="upgrade_plan"),
    
    path('customer/dashboard/',customer_dashboard, name='customer_dashboard'), 

    path('profile/', profile, name='profile'),
    path("swap-role/", swap_role, name="swap_role"),
    path('upgrade-to-admin/',upgrade_to_admin, name='upgrade_to_admin'),
    path('upgrade-to-customer/',upgrade_to_customer, name='upgrade_to_customer'),
]