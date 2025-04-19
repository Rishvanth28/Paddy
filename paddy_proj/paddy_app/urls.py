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
    path('admin_customer-list/',customers_under_admin, name='admin_customer_list'),
    path('customer/upgrade/', upgrade_to_admin, name='upgrade_to_admin'), 
    path('view-admins/', view_admins, name='view_admins'),
    path("view-customers/<int:admin_id>/", view_customers_under_admin, name="admin_customers"),
    path('superadmin/subscription-review/', superadmin_subscription, name='superadmin_subscription'),
    path('superadmin/review-subscription/', superadmin_subscription_review, name='superadmin_subscription_review'),
    path('upgrade-admin/',upgrade_to_customer, name='upgrade_admin'),
    path('demo/', demo, name='demo'),
    path("delete-admin/<int:admin_id>/", delete_admin, name="delete_admin"),
    path("delete-customer/<str:customer_id>/", delete_customer, name="delete_customer"),
    path('upgrade-success/',upgrade_success, name='upgrade_success'),
    path("admin-subscription/", admin_subscription_payment, name="admin_subscription_payment"),
    path("payment-success/", payment_success, name="payment_success"),
    path("customer-subscription/", customer_subscription_payment, name="customer_subscription_payment"),
    path("customer-payment-success/", customer_payment_success, name="customer_payment_success"),
    path("swap-role/", swap_role, name="swap_role"),
     path('admin-subscribers/', view_admin_subscribers, name='admin_subscribers'),



    ]



