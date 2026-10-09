from django.urls import path

from . import views

urlpatterns = [
    path("donor/requests/", views.donor_active_requests_view, name="donor_active_requests"),
    path("donor/appointments/book/", views.donor_book_appointment_view, name="donor_book_appointment"),
    path("donor/history/", views.donor_history_view, name="donor_history"),
    path("staff/appointments/", views.staff_appointments_view, name="staff_appointments"),
]