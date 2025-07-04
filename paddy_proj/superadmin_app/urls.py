from django.urls import path
from .views import *

app_name = 'superadmin_app'

urlpatterns = [
    path("dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("subscription/", superadmin_subscription, name="superadmin_subscription"),
    path("subscription-review/", superadmin_subscription_review, name="superadmin_subscription_review"),
    path("view-admins/", view_admins, name="view_admins"),
    path("view-customers/<int:admin_id>/", view_customers_under_admin, name="view_customers_under_admin"),
    path("customers-list/", customers_under_admin, name="customers_under_admin"),
    path("admin-subscribers/", view_admin_subscribers, name="view_admin_subscribers"),
    path("customer-subscribers/", view_customer_subscribers, name="view_customer_subscribers"),
    path("delete-admin/<int:admin_id>/", delete_admin, name="delete_admin"),
    path("delete-customer/<str:customer_id>/", delete_customer, name="delete_customer"),
]
