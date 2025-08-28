from django.urls import path
from . import views

urlpatterns = [
    path('devices/', views.list_devices, name='list_devices'),
    path('devices/<int:device_id>/last/', views.last_poll, name='last_poll'),
    path('devices/<int:device_id>/write_coils/', views.write_coils, name='write_coils'),
]
