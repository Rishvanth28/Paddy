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
    
    path('admin-orders/', admin_orders, name='admin_orders'),
    path('super-admin-orders/', super_admin_orders, name='super_admin_orders'),
    
    path('customer/dashboard/',customer_dashboard, name='customer_dashboard'), 
    path('customer-list/',customers_under_admin, name='customer_list'),
    path('admin_customer-list/',customers_under_admin, name='admin_customer_list'),
    path('view-admins/', view_admins, name='view_admins'),
    path("view-customers/<int:admin_id>/", view_customers_under_admin, name="admin_customers"),
    path('superadmin/subscription-review/', superadmin_subscription, name='superadmin_subscription'),
    path('superadmin/review-subscription/', superadmin_subscription_review, name='superadmin_subscription_review'),

    path('profile/', profile, name='profile'),
    path("delete-admin/<int:admin_id>/", delete_admin, name="delete_admin"),
    path("delete-customer/<str:customer_id>/", delete_customer, name="delete_customer"),
    path('upgrade-success/',upgrade_success, name='upgrade_success'),
    path("admin-subscription/", admin_subscription_payment, name="admin_subscription_payment"),
    path("payment-success/", payment_success, name="payment_success"),
    path("customer-subscription/", customer_subscription_payment, name="customer_subscription_payment"),
    path("customer-payment-success/", customer_payment_success, name="customer_payment_success"),
    path("swap-role/", swap_role, name="swap_role"),
    path('admin-subscribers/', view_admin_subscribers, name='admin_subscribers'),
    path('customer-subscribers/', view_customer_subscribers, name='customer_subscribers'),
    path('create_partial_payment_order/', create_partial_payment_order, name='create_partial_payment_order'),
    path('verify_partial_payment/', verify_partial_payment, name='verify_partial_payment'),
    path('ajax/create_admin_user_increase_order/', create_admin_user_increase_order, name='create_admin_user_increase_order'),
    path('ajax/verify_admin_user_increase_payment/', verify_admin_user_increase_payment, name='verify_admin_user_increase_payment'),    path('upgrade-to-admin/',upgrade_to_admin, name='upgrade_to_admin'),
    path('upgrade-to-customer/',upgrade_to_customer, name='upgrade_to_customer'),
    path("create-customer-signup/", create_customer_signup, name="create_customer_signup"),
    path("create-admin-signup/", create_admin_signup, name="create_admin_signup"),    # Notification URLs
    path('customer/notifications/', customer_notifications, name='customer_notifications'),
    path('admin-notifications/', admin_notifications, name='admin_notifications'),
    path('superadmin/notifications/', superadmin_notifications, name='superadmin_notifications'),
    path('mark_notification_read/', mark_notification_read, name='mark_notification_read'),
    path('mark_all_notifications_read/', mark_all_notifications_read, name='mark_all_notifications_read'),
    path('delete_notifications/', delete_notifications, name='delete_notifications'),
    # Reports URLs
    path('unified-report/', unified_report, name='unified_report'),
    path('download-report-excel/', download_report_excel, name='download_report_excel'),
    path("download-invoice-pdf/", download_invoice_pdf, name="download_invoice_pdf"),
]