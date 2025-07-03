from django.urls import path
from . import views

app_name = 'login_app'

urlpatterns = [
    # Login related views
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('create-admin-signup/', views.create_admin_signup, name='create_admin_signup'),
    path('create-customer-signup/', views.create_customer_signup, name='create_customer_signup'),
    path('admin-login-submit/', views.admin_login_submit, name='admin_login_submit'),
    path('swap-role/', views.swap_role, name='swap_role'),
]
