from django.urls import path
from .views import *


urlpatterns = [
    path("", login_view, name="login"),  # Login page
    path("superadmin-dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("customer-dashboard/", customer_dashboard, name="customer_dashboard"),
    path("logout/", logout_view, name="logout"), 
    path("create-admin/", create_admin, name="create_admin"),
    path("create-customer/", create_customer, name="create_customer"),
    path("onboard/", create_admin, name="onboard"),
    path('place_order/', place_order, name='place_order'),
    path('customer_orders/', customer_orders, name='customer_orders'),
    path('customer_orders/payment/', payment, name='payment'),
    path('customer_orders/delivery/', customer_delivery_validation, name='delivery'),
    path("admin-create-customer/", create_customer, name="customer_onboard"),
    path("admin-place-order/", place_order, name="admin_place_order"),
    path("admin-add-subscription/", admin_add_subscription, name="admin_add_subscription"),
    path("upgrade-plan/", upgrade_plan, name="upgrade_plan"),
    path('customer/upgrade/', upgrade_to_admin, name='upgrade_to_admin'),
    path('customer/dashboard/',customer_dashboard, name='customer_dashboard'), 
    path('customer-list/',customers_under_admin, name='customer_list'),
    path('customer/upgrade/', upgrade_to_admin, name='upgrade_to_admin'), 
    path('view-admins/', view_admins, name='view_admins'),
    path('admin/<int:admin_id>/customers/', view_customers_under_admin, name='admin_customers'),
]