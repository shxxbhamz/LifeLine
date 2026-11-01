from django.shortcuts import redirect, render

from appointments.models import Appointments
from core.models import StaffProfiles
from .models import EmergencyRequests


def staff_emergencies_view(request):
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    user_id = request.session.get("user_id")

    try:
        staff_profile = StaffProfiles.objects.select_related(
            "facility"
        ).get(user_id=user_id)
    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    emergency_requests = EmergencyRequests.objects.none()
    responding_emergency_donors = Appointments.objects.none()

    if staff_profile.facility:
        facility = staff_profile.facility

        emergency_requests = EmergencyRequests.objects.filter(
            facility=facility,
        ).order_by("-created_at")

        responding_emergency_donors = (
            Appointments.objects.filter(
                facility=facility,
                appointment_source="EMERGENCY",
            )
            .select_related(
                "donor",
                "donor__user",
            )
            .order_by("-id")
        )

    context = {
        "staff_profile": staff_profile,
        "emergency_requests": emergency_requests,
        "responding_emergency_donors": responding_emergency_donors,
    }

    return render(
        request,
        "organization/emergency.html",
        context,
    )


def staff_audit_log(request):
    # Only logged-in hospital staff can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # Display the Broadcast Audit Log page.
    return render(request, "organization/audit_log.html")