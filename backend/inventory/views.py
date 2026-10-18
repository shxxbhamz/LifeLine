from django.shortcuts import redirect, render

from core.models import StaffProfiles
from .models import BloodInventory


def staff_inventory(request):
    # Only logged-in hospital staff can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    user_id = request.session["user_id"]

    # Find the staff profile so we know which hospital/blood bank
    # this logged-in user belongs to.
    try:
        staff_profile = StaffProfiles.objects.get(user_id=user_id)
    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    facility = staff_profile.facility

    # Retrieve all inventory records belonging only to this facility.
    inventory_records = BloodInventory.objects.filter(
        facility=facility
    ).order_by("blood_type", "component_type")

    # Send both the facility and inventory records to the HTML template.
    context = {
        "facility": facility,
        "inventory_records": inventory_records,
    }

    return render(
        request,
        "organization/inventory.html",
        context,
    )