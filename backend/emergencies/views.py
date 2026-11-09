
import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from appointments.models import Appointments, Donations
from core.models import StaffProfiles
from core.utils import send_donation_thank_you_email
from inventory.models import BloodInventory, InventoryTransactions
from core.utils import send_donation_thank_you_email

from .models import EmergencyRequests, RequestMatches
from .matching import run_emergency_matching

#Heer Patel#
@login_required
@require_POST
def mark_donation_used_view(request, match_id):
    # Ensure only hospital staff can trigger this action
    if request.session.get("role") != "HOSPITAL_STAFF":
        messages.error(request, "Unauthorized access.")
        return redirect("login")
    
    try:
        # Look up the responding donor match record
        match_record = RequestMatches.objects.select_related('donor', 'request').get(id=match_id)
        donor_profile = match_record.donor
        
        # Prevent double-counting if already used
        if getattr(match_record, 'is_used', False):
            messages.warning(request, "This donation has already been marked as used.")
            return redirect(request.META.get('HTTP_REFERER', 'staff_audit_log'))

        # Use an atomic database transaction to update the match status and log a completed appointment
        with transaction.atomic():
            match_record.is_used = True
            match_record.save()

            # Create a completed appointment record so the donor's dashboard 
            # dynamically increments its total donations and lives saved count
            Appointments.objects.create(
                donor=donor_profile,
                facility=match_record.request.facility,
                donation_type=match_record.request.component_type,
                appointment_source='EMERGENCY',
                scheduled_at=timezone.now(),
                status='COMPLETED',
                notes=f"Emergency donation fulfilled for request #{match_record.request.id}"
            )

        messages.success(request, "Donation marked as used successfully! Donor metrics updated.")

    except RequestMatches.DoesNotExist:
        messages.error(request, "Donation match record not found.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    # Redirect back to whichever staff page they submitted from
    return redirect(request.META.get('HTTP_REFERER', 'staff_audit_log'))

#Heer Patel#

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
    responding_emergency_donors = RequestMatches.objects.none()
    emergency_map_data = []

    if staff_profile.facility:
        facility = staff_profile.facility

        emergency_requests = EmergencyRequests.objects.filter(
            facility=facility,
        ).order_by("-created_at")

        responding_emergency_donors = (
            RequestMatches.objects.filter(
                request__facility=facility,
                response_status="ACCEPTED",
            )
            .select_related(
                "request",
                "donor",
                "donor__user",
            )
            .order_by("-responded_at", "-id")
        )

        # Prepare map data only for ongoing emergency requests.
        if facility.latitude is not None and facility.longitude is not None:
            active_emergencies = emergency_requests.filter(
                status__in=["OPEN", "MATCHING", "ACTIVE"]
            )

            for emergency in active_emergencies:
                donor_locations = []

                # Only donors matched to this emergency are included.
                matches = RequestMatches.objects.filter(
                    request=emergency,
                    response_status__in=["PENDING", "ACCEPTED"],
                ).select_related("donor")

                for match in matches:
                    donor = match.donor

                    if donor.latitude is None or donor.longitude is None:
                        continue

                    # Pending donors must have been notified successfully.
                    if (
                        match.response_status == "PENDING"
                        and match.notification_status not in ["SENT", "VIEWED"]
                    ):
                        continue

                    donor_locations.append({
                        "latitude": float(donor.latitude),
                        "longitude": float(donor.longitude),
                        "status": match.response_status,
                    })

                emergency_map_data.append({
                    "id": emergency.id,
                    "blood_type": emergency.required_blood_type,
                    "radius_km": float(emergency.radius_km),
                    "latitude": float(facility.latitude),
                    "longitude": float(facility.longitude),
                    "donors": donor_locations,
                })

    context = {
        "staff_profile": staff_profile,
        "emergency_requests": emergency_requests,
        "responding_emergency_donors": responding_emergency_donors,
        "emergency_form_token": uuid.uuid4().hex,
        "emergency_map_data": emergency_map_data,
    }

    return render(
        request,
        "organization/emergency.html",
        context,
    )



@require_POST
def record_appointment_donation_view(request, appointment_id):

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

        if not staff_profile.facility:
            messages.error(
                request,
                "Your staff account is not connected to a facility."
            )
            return redirect("staff_audit_log")

        with transaction.atomic():

            appointment = Appointments.objects.select_for_update().select_related(
                "donor",
                "donor__user",
                "facility",
            ).get(
                id=appointment_id,
                facility=staff_profile.facility,
                status="CONFIRMED",
            )

            # Prevent duplicate donation records.
            donation, created = Donations.objects.get_or_create(
                appointment=appointment,
                defaults={
                    "actual_component_type": appointment.donation_type,
                    "recorded_by": staff_profile,
                    "completed_at": timezone.now(),
                    "quantity_units": 1,
                    "notes": "Donation marked as collected by hospital staff.",
                },
            )

        if created:

            # Send congratulatory email to the donor.
            donor_user = appointment.donor.user

            send_donation_thank_you_email(
                user_email=donor_user.email,
                first_name=donor_user.first_name,
                facility_name=appointment.facility.name,
                donation_type=appointment.donation_type,
            )

            messages.success(
                request,
                "Donation successfully marked as donated!"
            )

        else:
            messages.info(
                request,
                "This donation has already been recorded."
            )

    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    except Appointments.DoesNotExist:
        messages.error(
            request,
            "Appointment not found or unavailable."
        )

    except Exception as error:
        messages.error(
            request,
            f"Unable to record donation: {error}"
        )

    return redirect("staff_audit_log")


def staff_audit_log(request):

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

    confirmed_appointments = Appointments.objects.none()
    donated_appointment_ids = set()

    if staff_profile.facility:

        confirmed_appointments = (
            Appointments.objects.filter(
                facility=staff_profile.facility,
                status="CONFIRMED",
            )
            .select_related(
                "donor",
                "donor__user",
                "facility",
                "request_match",
            )
            .order_by("-scheduled_at")
        )

        donated_appointment_ids = set(
            Donations.objects.filter(
                appointment__facility=staff_profile.facility
            ).values_list(
                "appointment_id",
                flat=True,
            )
        )

    context = {
        "staff_profile": staff_profile,
        "confirmed_appointments": confirmed_appointments,
        "donated_appointment_ids": donated_appointment_ids,
    }

    return render(
        request,
        "organization/audit_log.html",
        context,
    )

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
        emergency_request = EmergencyRequests.objects.create(
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

    try:
        matched_donors = run_emergency_matching(
            emergency_request
        )

    except Exception:
        # The emergency request itself has already been saved.
        # Matching failures must not destroy the request.
        messages.warning(
            request,
            "Emergency request was created, but donor matching could not be completed.",
        )

    else:
        if matched_donors:
            messages.success(
                request,
                f"Emergency request created and {len(matched_donors)} donor candidate(s) matched.",
            )
        else:
            messages.warning(
                request,
                "Emergency request created, but no eligible donor candidates were found within the selected radius.",
            )

    return redirect("staff_emergencies")