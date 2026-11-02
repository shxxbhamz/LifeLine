from django.urls import path

from . import views


urlpatterns = [
    path("emergency/respond/<str:token>/", views.emergency_screening_view, name="emergency_screening"),
    path("emergency/respond/<str:token>/decision/", views.emergency_response_view, name="emergency_response"),
]