from django.shortcuts import redirect, render


def staff_emergencies_view(request):
    # Only logged-in hospital staff can access emergency dispatches.
    if request.session.get("user_id") is None or request.session.get("role") != "HOSPITAL_STAFF":
        return redirect("login")

    # Display the existing emergency dispatches page.
    return render(request, "organization/emergency.html")


def staff_audit_log(request):
    # Only logged-in hospital staff can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # Display the Broadcast Audit Log page.
    return render(request, "organization/audit_log.html")