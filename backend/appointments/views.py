import uuid
import math

from django.contrib import messages
from django.shortcuts import redirect, render

from emergencies.models import RequestMatches
from django.utils import timezone

from core.models import StaffProfiles
from inventory.models import BloodInventory, InventoryTransactions
from core.utils import send_appointment_status_email
from .models import Appointments, DonationRequests
from core.models import DonorProfiles, Facilities
from emergencies.models import EmergencyRequests
from django.db import transaction, IntegrityError
from django.utils.dateparse import parse_datetime
import logging

logger = logging.getLogger(__name__)


def staff_create_donation_request_view(request):
    # Only logged-in hospital/blood-bank staff can create requests.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # This endpoint only accepts form submissions.
    if request.method != "POST":
        return redirect("staff_inventory")

    user_id = request.session["user_id"]

    try:
        staff_profile = StaffProfiles.objects.get(user_id=user_id)
    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    blood_type = request.POST.get("restock_blood_type", "").strip()
    component_type = request.POST.get("restock_component", "").strip()
    units_raw = request.POST.get("restock_units", "").strip()

    valid_blood_types = {
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-",
    }

    valid_components = {
        "WHOLE_BLOOD",
        "RED_BLOOD_CELLS",
        "PLATELETS",
        "PLASMA",
    }

    if blood_type not in valid_blood_types:
        messages.error(request, "Please select a valid blood type.")
        return redirect("staff_inventory")

    if component_type not in valid_components:
        messages.error(request, "Please select a valid donation component.")
        return redirect("staff_inventory")

    try:
        units_required = int(units_raw)
    except (TypeError, ValueError):
        messages.error(request, "Required units must be a valid whole number.")
        return redirect("staff_inventory")

    if units_required <= 0:
        messages.error(request, "Required units must be greater than 0.")
        return redirect("staff_inventory")

    facility = staff_profile.facility

    # Prevent multiple open requests for the same facility,
    # blood type and component.
    
    duplicate_request = DonationRequests.objects.filter(
        facility=facility,
        required_blood_type=blood_type,
        component_type=component_type,
        status="OPEN",
    ).first()

    if duplicate_request:
        confirm_add = request.POST.get("confirm_add_to_existing")

        if confirm_add == "1":
            duplicate_request.units_required += units_required
            duplicate_request.updated_at = timezone.now()

            duplicate_request.save(
                update_fields=[
                    "units_required",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"{units_required} additional unit(s) added to the existing "
                f"{blood_type} {component_type.replace('_', ' ').title()} request. "
                f"New total: {duplicate_request.units_required} unit(s).",
            )

            return redirect("staff_inventory")

        messages.error(
            request,
            "An open donation request already exists.",
        )
        return redirect("staff_inventory")
    
    now = timezone.now()

    DonationRequests.objects.create(
        facility=facility,
        created_by=staff_profile,
        required_blood_type=blood_type,
        component_type=component_type,
        units_required=units_required,
        status="OPEN",
        notes="Inventory restock donation request",
        idempotency_key=uuid.uuid4().hex,
        created_at=now,
        updated_at=now,
    )

    messages.success(
        request,
        f"Donation request created for {units_required} unit(s) of "
        f"{blood_type} {component_type.replace('_', ' ').title()}.",
    )

    return redirect("staff_inventory")


def donor_active_requests_view(request):
    # Only logged-in donors can access the Active Requests page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "DONOR"
    ):
        return redirect("login")

    user_id = request.session.get("user_id")

    try:
        donor_profile = DonorProfiles.objects.get(user_id=user_id)

        emergency_requests = EmergencyRequests.objects.filter(
            required_blood_type__iexact=donor_profile.blood_type,
            status__iexact="ACTIVE",
        ).select_related(
            "facility"
        ).order_by("-created_at")

        context = {
            "emergency_requests": emergency_requests,
        }

        return render(
            request,
            "donor/active_requests.html",
            context,
        )

    except DonorProfiles.DoesNotExist:
        return render(
            request,
            "donor/active_requests.html",
            {"emergency_requests": []},
        )


#Heer Patel#
def donor_book_appointment_view(request):
    # Only logged-in donors can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "DONOR"
    ):
        return redirect("login")

    user_id = request.session.get("user_id")

    try:
        donor_profile = DonorProfiles.objects.select_related(
            "user"
        ).get(user_id=user_id)

    except DonorProfiles.DoesNotExist:
        messages.error(request, "Donor profile not found.")
        return redirect("donor_dashboard")

    # Calculate distance between donor and facility.
    def calculate_distance(lat1, lon1, lat2, lon2):
        earth_radius = 6371

        lat1 = math.radians(float(lat1))
        lon1 = math.radians(float(lon1))
        lat2 = math.radians(float(lat2))
        lon2 = math.radians(float(lon2))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return earth_radius * c

    # Load actual facilities from Neon.
    facilities = list(Facilities.objects.all())

    for facility in facilities:

        facility.distance_km = None

        if (
            donor_profile.latitude is not None
            and donor_profile.longitude is not None
            and facility.latitude is not None
            and facility.longitude is not None
        ):
            facility.distance_km = calculate_distance(
                donor_profile.latitude,
                donor_profile.longitude,
                facility.latitude,
                facility.longitude,
            )

    # Facilities with known distances appear first.
    facilities.sort(
        key=lambda facility: (
            facility.distance_km is None,
            facility.distance_km
            if facility.distance_km is not None
            else float("inf"),
        )
    )

    # Process donor booking.
    if request.method == "POST":

        facility_id = request.POST.get("facility_id")
        donation_type = request.POST.get("donation_type")
        scheduled_at_raw = request.POST.get("scheduled_at")

        valid_donation_types = {
            "WHOLE_BLOOD",
            "RED_BLOOD_CELLS",
            "PLASMA",
            "PLATELETS",
        }

        if donation_type not in valid_donation_types:
            messages.error(
                request,
                "Please select a valid donation type."
            )
            return redirect("donor_book_appointment")

        try:
            facility = Facilities.objects.get(id=facility_id)
        except (Facilities.DoesNotExist, ValueError, TypeError):
            messages.error(
                request,
                "Please select a valid facility."
            )
            return redirect("donor_book_appointment")

        scheduled_at = parse_datetime(scheduled_at_raw)

        if scheduled_at is None:
            messages.error(
                request,
                "Please select a valid appointment date and time."
            )
            return redirect("donor_book_appointment")

        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(
                scheduled_at,
                timezone.get_current_timezone()
            )

        if scheduled_at <= timezone.now():
            messages.error(
                request,
                "Please select a future appointment date and time."
            )
            return redirect("donor_book_appointment")

        now = timezone.now()

        try:
            with transaction.atomic():

                Appointments.objects.create(
                    donor=donor_profile,
                    facility=facility,
                    donation_type=donation_type,
                    appointment_source="REGULAR",
                    scheduled_at=scheduled_at,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                )

        except IntegrityError:
            messages.error(
                request,
                "You already have an appointment at this date and time."
            )
            return redirect("donor_book_appointment")

        except Exception:
            logger.exception(
                "DONOR APPOINTMENT BOOKING FAILED: user_id=%s",
                user_id,
            )

            messages.error(
                request,
                "Unable to book your appointment. Please try again."
            )
            return redirect("donor_book_appointment")

        messages.success(
            request,
            "Your appointment request has been submitted. "
            "It is waiting for hospital staff confirmation."
        )

        return redirect("donor_book_appointment")

    context = {
        "nearby_facilities": facilities,
        "donor_name": donor_profile.user.first_name,
        "donor_blood_type": donor_profile.blood_type,
    }

    return render(
        request,
        "donor/book_an_appointment.html",
        context
    )
#Heer Patel#

def donor_history_view(request):
    # Only logged-in donors can access their donation history.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    # Display the donor's existing history page.
    return render(request, "donor/history.html")


def staff_appointments_view(request):
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

    scheduled_appointments = Appointments.objects.none()
    emergency_requests = EmergencyRequests.objects.none()
    responding_emergency_donors = Appointments.objects.none()

    if staff_profile.facility:
        facility = staff_profile.facility

        # Normal and restock-request appointments.
        # Emergency appointments are displayed separately below.
        scheduled_appointments = (
            Appointments.objects.filter(
                facility=facility,
            )
            .exclude(
                appointment_source="EMERGENCY",
            )
            .select_related(
                "donor",
                "donor__user",
            )
            .order_by("scheduled_at")
        )

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
        "scheduled_appointments": scheduled_appointments,
        "emergency_requests": emergency_requests,
        "responding_emergency_donors": responding_emergency_donors,
        "emergency_form_token": uuid.uuid4().hex,
    }

    return render(
        request,
        "organization/appointment.html",
        context,
    )


def staff_confirm_appointment_view(request, appointment_id):
    # Only hospital staff can confirm appointments.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    if request.method != "POST":
        return redirect("staff_appointments")

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
        return redirect("staff_appointments")

    try:
        with transaction.atomic():

            # Find and lock the normal appointment.
            appointment = (
                Appointments.objects.select_for_update()
                .select_related(
                    "donor",
                    "donor__user",
                    "facility",
                )
                .filter(
                    id=appointment_id,
                    facility=staff_profile.facility,
                )
                .exclude(appointment_source="EMERGENCY")
                .first()
            )

            if appointment is None:
                messages.error(
                    request,
                    "Appointment not found for your facility.",
                )
                return redirect("staff_appointments")

            if appointment.status != "PENDING":
                messages.error(
                    request,
                    "Only pending appointments can be confirmed.",
                )
                return redirect("staff_appointments")

            # Find and lock the matching inventory record.
            inventory = (
                BloodInventory.objects.select_for_update()
                .filter(
                    facility=appointment.facility,
                    blood_type=appointment.donor.blood_type,
                    component_type=appointment.donation_type,
                )
                .first()
            )

            if inventory is None:
                messages.error(
                    request,
                    "Inventory record not found for this blood type "
                    "and component.",
                )
                return redirect("staff_appointments")

            now = timezone.now()

            # Confirm appointment.
            appointment.status = "CONFIRMED"
            appointment.confirmed_by = staff_profile
            appointment.updated_at = now

            appointment.save(
                update_fields=[
                    "status",
                    "confirmed_by",
                    "updated_at",
                ]
            )

            # Increase inventory by one unit.
            inventory.units_available += 1
            inventory.updated_at = now

            inventory.save(
                update_fields=[
                    "units_available",
                    "updated_at",
                ]
            )

            # Record inventory transaction.
            InventoryTransactions.objects.create(
                inventory=inventory,
                changed_by=staff_profile,
                transaction_type="DONATION_RECEIVED",
                units_change=1,
                reason=f"Appointment #{appointment.id} confirmed",
                created_at=now,
            )

    except Exception:
        logger.exception(
            "CONFIRM APPOINTMENT FAILED: appointment_id=%s",
            appointment_id,
        )

        messages.error(
            request,
            "Could not confirm appointment or update inventory. "
            "Please check server logs.",
        )
        return redirect("staff_appointments")

    # Send confirmation email after the database transaction succeeds.
    try:
        send_appointment_status_email(
            user_email=appointment.donor.user.email,
            first_name=appointment.donor.user.first_name,
            facility_name=staff_profile.facility.name,
            scheduled_at=appointment.scheduled_at,
            donation_type=appointment.donation_type,
            status="CONFIRMED",
        )
    except Exception:
        logger.exception(
            "CONFIRMATION EMAIL FAILED: appointment_id=%s",
            appointment_id,
        )

    messages.success(
        request,
        "Appointment confirmed and inventory increased by 1 unit.",
    )

    return redirect("staff_appointments")
def staff_cancel_appointment_view(request, appointment_id):
    # Only hospital staff can cancel appointments.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # Cancellation must only happen through POST.
    if request.method != "POST":
        return redirect("staff_appointments")

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
        return redirect("staff_appointments")

    appointment = (
        Appointments.objects.select_related(
            "donor",
            "donor__user",
            "facility",
        )
        .filter(
            id=appointment_id,
            facility=staff_profile.facility,
        )
        .exclude(appointment_source="EMERGENCY")
        .first()
    )

    if appointment is None:
        messages.error(
            request,
            "Appointment not found for your facility.",
        )
        return redirect("staff_appointments")

    if appointment.status not in ["PENDING", "CONFIRMED"]:
        messages.error(
            request,
            "Only pending or confirmed appointments can be cancelled.",
        )
        return redirect("staff_appointments")

    now = timezone.now()

    appointment.status = "CANCELLED"
    appointment.cancelled_at = now
    appointment.updated_at = now

    appointment.save(
        update_fields=[
            "status",
            "cancelled_at",
            "updated_at",
        ]
    )

    send_appointment_status_email(
        user_email=appointment.donor.user.email,
        first_name=appointment.donor.user.first_name,
        facility_name=staff_profile.facility.name,
        scheduled_at=appointment.scheduled_at,
        donation_type=appointment.donation_type,
        status="CANCELLED",
    )

    messages.success(
        request,
        "Appointment cancelled successfully.",
    )

    return redirect("staff_appointments")

