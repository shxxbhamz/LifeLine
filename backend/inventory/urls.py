from django.urls import path
from . import views

urlpatterns = [
    path("staff/inventory/", views.staff_inventory, name="staff_inventory"),
]