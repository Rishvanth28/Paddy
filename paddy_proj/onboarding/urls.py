from django.urls import path
from . import views

app_name = 'onboarding'

urlpatterns = [
    path("onboard/", views.onboard, name="onboard"),
    path("create-admin/", views.create_admin, name="create_admin"),
    path("create-customer/", views.create_customer, name="create_customer"),
    path("admin-create-customer/", views.create_customer, name="customer_onboard"),
    path("customer-onboard-view/", views.customer_onboard_view, name="customer_onboard_view"),
    path("create-admin-signup/", views.create_admin_signup, name="create_admin_signup"),
    path("create-customer-signup/", views.create_customer_signup, name="create_customer_signup"),
]
