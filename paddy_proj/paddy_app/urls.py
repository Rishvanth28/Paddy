from django.urls import path
from .views import admin_list, admin_detail, customer_list, order_list, payment_list, subscription_list, login_view,home


urlpatterns = [
    path('',login_view, name='login'),
]
