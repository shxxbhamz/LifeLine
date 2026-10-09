from django.shortcuts import redirect, render


def donor_active_requests_view(request):
    # Only logged-in donors can access the Active Requests page.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    # Display the existing non-emergency donation requests page.
    return render(request, "donor/active_requests.html")


def donor_book_appointment_view(request):
    # Only logged-in donors can access the booking page.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    # Display the existing appointment booking page.
    return render(request, "donor/book_an_appointment.html")


def donor_history_view(request):
    # Only logged-in donors can access their donation history.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    # Display the donor's existing history page.
    return render(request, "donor/history.html")


def staff_appointments_view(request):
    # Only logged-in hospital staff can access this page.
    if request.session.get("user_id") is None or request.session.get("role") != "HOSPITAL_STAFF":
        return redirect("login")

    # Display the existing staff appointments page.
    return render(request, "organization/appointment.html")