from django.urls import path

from . import views

urlpatterns = [
    # Authentication page routes
    path("login/", views.login_view, name="login"),
    path("register/donor/", views.donor_signup_view, name="donor_signup"),
    path("register/staff/", views.organization_signup_view, name="organization_signup"),
    path("donor/dashboard/", views.donor_dashboard_view, name="donor_dashboard"),
    path("staff/dashboard/", views.staff_dashboard_view, name="staff_dashboard"),
    path("logout/", views.logout_view, name="logout"),
]