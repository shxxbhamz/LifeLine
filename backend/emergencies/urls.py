from django.urls import path
from . import views

urlpatterns = [
    path("staff/emergencies/", views.staff_emergencies_view, name="staff_emergencies"),
    path("staff/audit-log/", views.staff_audit_log, name="staff_audit_log"),
    path("staff/emergencies/create/", views.staff_create_emergency_request_view, name="staff_create_emergency_request"),
]