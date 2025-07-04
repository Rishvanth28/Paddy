from django.urls import path
from django.shortcuts import redirect
from .views import *

app_name = 'admin_app'

urlpatterns = [
    
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin-add-subscription/", admin_add_subscription, name="admin_add_subscription"),
    path("admin-customer-list/", admin_customer_list, name="admin_customer_list"),
    path("upgrade-plan/", upgrade_plan, name="upgrade_plan"),
    path('upgrade-to-customer/',upgrade_to_customer, name='upgrade_to_customer'),
    
]