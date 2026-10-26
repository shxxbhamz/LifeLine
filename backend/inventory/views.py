from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import StaffProfiles

from .models import BloodInventory, InventoryTransactions
from appointments.models import DonationRequests


BLOOD_TYPES = [
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
]

COMPONENT_TYPES = [
    "WHOLE_BLOOD",
    "RED_BLOOD_CELLS",
    "PLATELETS",
    "PLASMA",
]


def staff_inventory(request):
    # Only logged-in hospital staff can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    user_id = request.session["user_id"]

    try:
        staff_profile = StaffProfiles.objects.get(user_id=user_id)
    except StaffProfiles.DoesNotExist:
        request.session.flush()
        return redirect("login")

    facility = staff_profile.facility

    # Make sure this facility has all 32 inventory combinations.
    for blood_type in BLOOD_TYPES:
        for component_type in COMPONENT_TYPES:
            BloodInventory.objects.get_or_create(
                facility=facility,
                blood_type=blood_type,
                component_type=component_type,
                defaults={
                    "units_available": 0,
                    "low_threshold": 5,
                    "critical_threshold": 2,
                    "updated_at": timezone.now(),
                },
            )

    # ---------------------------------------------------------
    # HANDLE INVENTORY UPDATE
    # ---------------------------------------------------------
    if request.method == "POST":
        blood_type = request.POST.get("blood_type", "").strip()

        if blood_type not in BLOOD_TYPES:
            messages.error(request, "Invalid blood type.")
            return redirect("staff_inventory")

        requested_changes = {
            "WHOLE_BLOOD": {
                "action": request.POST.get("action_whole_blood"),
                "units": request.POST.get("units_whole_blood", "0"),
            },
            "RED_BLOOD_CELLS": {
                "action": request.POST.get("action_red_blood_cells"),
                "units": request.POST.get("units_red_blood_cells", "0"),
            },
            "PLATELETS": {
                "action": request.POST.get("action_platelets"),
                "units": request.POST.get("units_platelets", "0"),
            },
            "PLASMA": {
                "action": request.POST.get("action_plasma"),
                "units": request.POST.get("units_plasma", "0"),
            },
        }

        # Validate all submitted values before changing the database.
        validated_changes = {}

        for component_type, change in requested_changes.items():
            action = change["action"]

            if action not in ("add", "delete"):
                messages.error(
                    request,
                    f"Invalid action for {component_type}.",
                )
                return redirect("staff_inventory")

            try:
                units = int(change["units"])
            except (TypeError, ValueError):
                messages.error(
                    request,
                    "Inventory units must be valid whole numbers.",
                )
                return redirect("staff_inventory")

            if units < 0:
                messages.error(
                    request,
                    "Inventory units cannot be negative.",
                )
                return redirect("staff_inventory")

            # A value of 0 means no change for this component.
            if units == 0:
                continue

            validated_changes[component_type] = {
                "action": action,
                "units": units,
            }

        if not validated_changes:
            messages.error(
                request,
                "Enter at least one inventory change.",
            )
            return redirect("staff_inventory")

        try:
            # All inventory changes succeed together or none are saved.
            with transaction.atomic():

                inventory_records = {}

                # Lock the affected rows while we validate/update them.
                for component_type, change in validated_changes.items():
                    inventory = BloodInventory.objects.select_for_update().get(
                        facility=facility,
                        blood_type=blood_type,
                        component_type=component_type,
                    )

                    inventory_records[component_type] = inventory

                    # Prevent stock from dropping below zero.
                    if (
                        change["action"] == "delete"
                        and inventory.units_available < change["units"]
                    ):
                        raise ValueError(
                            f"Not enough {component_type.replace('_', ' ').title()} "
                            f"units for {blood_type}. "
                            f"Current stock: {inventory.units_available}."
                        )

                # Only update after every requested change passes validation.
                for component_type, change in validated_changes.items():
                    inventory = inventory_records[component_type]
                    units = change["units"]

                    if change["action"] == "add":
                        units_change = units
                    else:
                        units_change = -units

                    inventory.units_available += units_change
                    inventory.updated_at = timezone.now()
                    inventory.save(
                        update_fields=[
                            "units_available",
                            "updated_at",
                        ]
                    )

                    # Keep an audit trail of every inventory change.
                    InventoryTransactions.objects.create(
                        inventory=inventory,
                        changed_by=staff_profile,
                        transaction_type="MANUAL_ADJUSTMENT",
                        units_change=units_change,
                        reason="Inventory updated through staff inventory page",
                        created_at=timezone.now(),
                    )

        except ValueError as error:
            messages.error(request, str(error))
            return redirect("staff_inventory")

        messages.success(
            request,
            f"{blood_type} inventory updated successfully.",
        )

        # Redirect prevents duplicate updates if the user refreshes the page.
        return redirect("staff_inventory")

    # ---------------------------------------------------------
    # DISPLAY INVENTORY
    # ---------------------------------------------------------
    inventory_records = BloodInventory.objects.filter(
        facility=facility
    )

    inventory_rows = []

    for blood_type in BLOOD_TYPES:
        row = {
            "blood_type": blood_type,
            "whole_blood": 0,
            "red_blood_cells": 0,
            "platelets": 0,
            "plasma": 0,
            "status": "NORMAL",
        }

        records = inventory_records.filter(
            blood_type=blood_type
        )

        for record in records:
            if record.component_type == "WHOLE_BLOOD":
                row["whole_blood"] = record.units_available

            elif record.component_type == "RED_BLOOD_CELLS":
                row["red_blood_cells"] = record.units_available

            elif record.component_type == "PLATELETS":
                row["platelets"] = record.units_available

            elif record.component_type == "PLASMA":
                row["plasma"] = record.units_available

            if record.units_available <= record.critical_threshold:
                row["status"] = "CRITICAL"

            elif (
                record.units_available <= record.low_threshold
                and row["status"] != "CRITICAL"
            ):
                row["status"] = "LOW"

        inventory_rows.append(row)

    open_donation_requests = {}

    for donation_request in DonationRequests.objects.filter(
        facility=facility,
        status="OPEN",
    ):
        key = (
            donation_request.required_blood_type
            + "|"
            + donation_request.component_type
        )

        open_donation_requests[key] = donation_request.units_required
    
    context = {
        "facility": facility,
        "inventory_rows": inventory_rows,
        "open_donation_requests": open_donation_requests,
    }

    return render(
        request,
        "organization/inventory.html",
        context,
    )