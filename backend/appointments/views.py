import uuid

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import StaffProfiles
from .models import DonationRequests

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



def staff_appointments_view(request):
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    user_id = request.session.get("user_id")

    print("\n===== STAFF APPOINTMENTS DEBUG =====")
    print("Session user_id:", user_id)
    print("Session role:", request.session.get("role"))

    scheduled_appointments = []
    emergency_requests = []

    try:
        staff_profile = StaffProfiles.objects.select_related(
            "facility"
        ).get(user_id=user_id)

        print("Staff profile found:", staff_profile)
        print("Staff facility ID:", staff_profile.facility_id)

        if staff_profile.facility_id:
            facility_id = staff_profile.facility_id

            scheduled_appointments = list(
                Appointments.objects.filter(
                    facility_id=facility_id
                ).select_related(
                    "donor__user"
                ).order_by("-id")
            )

            emergency_requests = list(
                EmergencyRequests.objects.filter(
                    facility_id=facility_id
                ).order_by("-created_at")
            )

            print("Appointments found:", len(scheduled_appointments))

            for appt in scheduled_appointments:
                print(
                    "Appointment ID:", appt.pk,
                    "| Facility ID:", appt.facility_id,
                    "| Donor ID:", appt.donor_id,
                    "| Scheduled:", appt.scheduled_at,
                    "| Status:", appt.status,
                )

        else:
            print("ERROR: Staff has no facility assigned.")

    except StaffProfiles.DoesNotExist:
        print("ERROR: No StaffProfiles record for user:", user_id)

    except Exception as exc:
        print("APPOINTMENT DEBUG ERROR:", repr(exc))
        raise

    context = {
        "scheduled_appointments": scheduled_appointments,
        "emergency_requests": emergency_requests,
    }

    print("====================================\n")

    return render(
        request,
        "organization/appointment.html",
        context,
    )
