from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django Admin Panel
    path('api/', include('paddy_app.urls')),  # API routes for your app
    path('', include('paddy_app.urls')),  # Set paddy_app as the main app
    path('orders/', include('orders_app.urls')),  # Orders app URLs
    path('payment/', include('payment_app.urls')),  # Payment app URLs
    path('login/', include('login_app.urls')),  # Login app URLs
    path('superadmin/', include('superadmin_app.urls')),  # Superadmin app URLs
    path('reports/', include('reports.urls')),  # Reports app URLs
    path('notifications/', include('notifications.urls')),  # Notifications app URLs
    path('onboarding/', include('onboarding.urls')),  # Onboarding app URLs
]
