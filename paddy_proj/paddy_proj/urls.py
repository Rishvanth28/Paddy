from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin Panel - Keep this at the top for priority
    #path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', include('login_app.urls')),
    
    # Core apps with specific prefixes to avoid conflicts
    path('api/', include('paddy_app.urls')),  # API routes
    path('admin-panel/', include('admin_app.urls')),  # Admin app URLs
    path('customer/', include('customer_app.urls')),  # Customer app URLs
    
    # Other feature apps
    path('orders/', include('orders_app.urls')),
    path('payment/', include('payment_app.urls')),
    path('superadmin/', include('superadmin_app.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    path('onboarding/', include('onboarding.urls')),
    
    # Main app routes - Keep this last to catch remaining URLs
    path('', include('paddy_app.urls')),
]
