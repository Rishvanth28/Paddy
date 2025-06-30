from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django Admin Panel
    path('api/', include('paddy_app.urls')),  # API routes for your app
    path('', include('paddy_app.urls')),  # Set paddy_app as the main app
    path('reports/', include('reports.urls')),  # Reports app URLs
]
