from django.urls import path
from . import views

urlpatterns = [
    path('devices/', views.list_devices, name='list_devices'),
    path('devices/<int:device_id>/last/', views.last_poll, name='last_poll'),
    path('devices/<int:device_id>/write_coils/', views.write_coils, name='write_coils'),
    path('devices/<int:device_id>/cards/<int:card_id>/series/', views.card_series, name='card_series'),
    path('devices/<int:device_id>/actions/<int:action_id>/execute/', views.execute_action, name='execute_action'),
]
