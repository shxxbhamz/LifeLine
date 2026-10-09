from django.shortcuts import render, redirect


def staff_inventory(request):
    # Only logged-in hospital staff can access this page.
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "HOSPITAL_STAFF"
    ):
        return redirect("login")

    # Display the inventory HTML page.
    return render(request, "organization/inventory.html")