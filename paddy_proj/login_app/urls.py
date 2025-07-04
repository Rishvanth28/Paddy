from django.urls import path
from .views import *

app_name = 'login_app'

urlpatterns = [
    path("", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("admin-login-submit/", admin_login_submit, name="admin_login_submit"),
]