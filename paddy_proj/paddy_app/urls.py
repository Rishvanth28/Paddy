from django.urls import path
from .views import *


urlpatterns = [
    path("", login_view, name="login"),  # Login page
    path("superadmin-dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("customer-dashboard/", customer_dashboard, name="customer_dashboard"),
    path("logout/", logout_view, name="logout"), 
]
