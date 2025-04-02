from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django Admin Panel
    path('api/', include('paddy_app.urls')),  # Include app-level URLs
]
