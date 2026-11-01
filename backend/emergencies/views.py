import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db import IntegrityError

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
        "emergency_form_token": uuid.uuid4().hex,
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


def staff_create_emergency_request_view(request):
    # Only authenticated hospital staff may create emergency requests.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # Creating an emergency request must only happen through POST.
    if request.method != "POST":
        return redirect("staff_emergencies")

    user_id = request.session.get("user_id")

    try:
        staff_profile = StaffProfiles.objects.select_related(
            "facility"
        ).get(user_id=user_id)
    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    if not staff_profile.facility:
        messages.error(
            request,
            "Your staff account is not connected to a facility.",
        )
        return redirect("staff_emergencies")

    # Read submitted values.
    required_blood_type = request.POST.get(
        "required_blood_type", ""
    ).strip().upper()

    component_type = request.POST.get(
        "component_type", ""
    ).strip().upper()

    units_raw = request.POST.get(
        "units_required", ""
    ).strip()

    urgency = request.POST.get(
        "urgency", ""
    ).strip().upper()

    radius_raw = request.POST.get(
        "radius_km", "25"
    ).strip()

    notes = request.POST.get(
        "notes", ""
    ).strip()

    idempotency_key = request.POST.get(
        "idempotency_key", ""
    ).strip()

    # Allowed values must match the database schema.
    valid_blood_types = {
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-",
        "ANY",
    }

    valid_components = {
        "WHOLE_BLOOD",
        "RED_BLOOD_CELLS",
        "PLASMA",
        "PLATELETS",
    }

    valid_urgencies = {
        "URGENT",
        "CRITICAL",
    }

    # Validate blood type.
    if required_blood_type not in valid_blood_types:
        messages.error(
            request,
            "Please select a valid blood type.",
        )
        return redirect("staff_emergencies")

    # Validate component.
    if component_type not in valid_components:
        messages.error(
            request,
            "Please select a valid blood component.",
        )
        return redirect("staff_emergencies")

    # Validate units.
    try:
        units_required = int(units_raw)

        if units_required <= 0:
            raise ValueError

    except (TypeError, ValueError):
        messages.error(
            request,
            "Units required must be a whole number greater than 0.",
        )
        return redirect("staff_emergencies")

    # Validate urgency.
    if urgency not in valid_urgencies:
        messages.error(
            request,
            "Please select a valid urgency level.",
        )
        return redirect("staff_emergencies")

    # Validate radius.
    try:
        radius_km = Decimal(radius_raw)

        if radius_km <= 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError):
        messages.error(
            request,
            "Search radius must be greater than 0 km.",
        )
        return redirect("staff_emergencies")

    now = timezone.now()

    if not idempotency_key or len(idempotency_key) > 64:
        messages.error(
            request,
            "Invalid emergency request submission. Please try again.",
        )
        return redirect("staff_emergencies")

    if EmergencyRequests.objects.filter(
        idempotency_key=idempotency_key
    ).exists():
        messages.error(
            request,
            "This emergency request has already been submitted.",
        )
        return redirect("staff_emergencies")

    try:
        EmergencyRequests.objects.create(
            facility=staff_profile.facility,
            created_by=staff_profile,
            required_blood_type=required_blood_type,
            component_type=component_type,
            units_required=units_required,
            urgency=urgency,
            radius_km=radius_km,
            status="OPEN",
            notes=notes or None,
            created_at=now,
            updated_at=now,
            idempotency_key=idempotency_key,
        )

    except IntegrityError:
        messages.error(
            request,
            "This emergency request has already been submitted.",
        )
        return redirect("staff_emergencies")

    messages.success(
        request,
        "Emergency request created successfully.",
    )

    return redirect("staff_emergencies")