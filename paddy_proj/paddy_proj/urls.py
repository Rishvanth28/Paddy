from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django Admin Panel
    
    # New microservice apps
    path('', include('login_app.urls')),  # Login app as root
    path('admin-app/', include('admin_app.urls')),  # Admin app URLs
    path('customer-app/', include('customer_app.urls')),  # Customer app URLs
    path('superadmin-app/', include('superadmin_app.urls')),  # Superadmin app URLs
    path('profile/', include('profile_app.urls')),  # Profile app URLs
    
    # Existing apps
    path('api/', include('paddy_app.urls')),  # API routes for remaining paddy_app
    path('reports/', include('reports_app.urls')),  # Reports app URLs
    path('notifications/', include('notifications_app.urls')),  # Notifications app URLs
    path('onboarding/', include('onboarding_app.urls')),  # Onboarding app URLs
]
