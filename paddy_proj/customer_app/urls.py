from django.urls import path
from django.shortcuts import redirect
from .views import *

app_name = 'customer_app'

urlpatterns = [

    path("customer-dashboard/", customer_dashboard, name="customer_dashboard"),
    path('upgrade-to-admin/',upgrade_to_admin, name='upgrade_to_admin'),
    
]