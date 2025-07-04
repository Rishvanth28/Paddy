from django.urls import path
from django.shortcuts import redirect
from .views import *


urlpatterns = [

    path('profile/', profile, name='profile'),
    path("swap-role/", swap_role, name="swap_role"),
    path('get-admins/', get_admins_api, name='get_admins_api'),
    path('update-order-delivery-status/', update_order_delivery_status_api, name='update_order_delivery_status_api'),

]