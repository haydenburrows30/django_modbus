from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('modbusapp.urls')),          # pages: / and /dashboard/
    path('api/', include('modbusapp.api_urls')),  # APIs under /api/
]
