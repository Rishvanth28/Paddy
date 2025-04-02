from django.urls import path
from .views import admin_list, admin_detail, customer_list, order_list, payment_list, subscription_list, login_view,home


urlpatterns = [
    # path('', home, name='home'),
    path('',login_view, name='login'),
    # path('login/', login_view, name='login'),
    
    # ✅ Admin URLs
    path('admins/', admin_list, name='admin_list'),
    path('admins/<int:admin_id>/', admin_detail, name='admin_detail'),

    # ✅ Customer URLs
    path('customers/', customer_list, name='customer_list'),

    # ✅ Orders URLs
    path('orders/', order_list, name='order_list'),

    # ✅ Payments URLs
    path('payments/', payment_list, name='payment_list'),

    # ✅ Subscriptions URLs
    path('subscriptions/', subscription_list, name='subscription_list'),
]
