from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import DonorProfiles, Facilities, StaffProfiles, Users


def login_view(request):
    return render(request, "core/login.html")


def donor_signup_view(request):
    # A GET request only displays the registration page.
    if request.method == "GET":
        return render(request, "core/donor_signup.html")

    # Read the values submitted by the donor registration form.
    first_name = request.POST.get("firstName", "").strip()
    last_name = request.POST.get("lastName", "").strip()
    username = request.POST.get("username", "").strip().lower()
    email = request.POST.get("email", "").strip().lower()
    phone = request.POST.get("phone", "").strip()
    date_of_birth = request.POST.get("dob", "")
    street_address = request.POST.get("fullAddress", "").strip()
    city = request.POST.get("city", "").strip()
    province = request.POST.get("Province", "").strip()
    country = request.POST.get("country", "").strip()
    postal_code = request.POST.get("pincode", "").strip()
    blood_type = request.POST.get("bloodGroup", "")
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirmPassword", "")
    terms_accepted = request.POST.get("terms")

    # Preserve non-sensitive form values if validation fails.
    # Passwords are intentionally excluded for security.
    form_data = {
        "firstName": first_name,
        "lastName": last_name,
        "username": username,
        "email": email,
        "phone": phone,
        "dob": date_of_birth,
        "fullAddress": street_address,
        "city": city,
        "Province": province,
        "country": country,
        "pincode": postal_code,
        "bloodGroup": blood_type,
        "terms": bool(terms_accepted),
    }

    # Basic validation before anything is written to the database.
    if not username.startswith("do"):
        return render(
            request,
            "core/donor_signup.html",
            {"error": "Donor usernames must begin with 'do'.", "form_data": form_data},
        )

    if password != confirm_password:
        return render(
            request,
            "core/donor_signup.html",
            {"error": "Passwords do not match.", "form_data": form_data},
        )

    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "core/donor_signup.html",
            {"error": "That username is already in use.", "form_data": form_data},
        )

    if Users.objects.filter(email=email).exists():
        return render(
            request,
            "core/donor_signup.html",
            {"error": "An account with that email already exists.", "form_data": form_data},
        )

    if not terms_accepted:
        return render(
            request,
            "core/donor_signup.html",
            {"error": "You must accept the terms and privacy policy.", "form_data": form_data},
        )

    now = timezone.now()

    # Create the user and donor profile as one database transaction.
    # If creating either record fails, neither record is permanently saved.
    with transaction.atomic():
        user = Users.objects.create(
            username=username,
            email=email,
            password_hash=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role="DONOR",
            account_status="ACTIVE",
            terms_accepted_at=now,
            created_at=now,
            updated_at=now,
        )

        DonorProfiles.objects.create(
            user=user,
            phone=phone,
            date_of_birth=date_of_birth,
            blood_type=blood_type,
            street_address=street_address,
            city=city,
            province=province,
            postal_code=postal_code,
            country=country,
            emergency_available=True,
        )

    # Registration succeeded, so send the donor to the login page.
    return redirect("login")


def organization_signup_view(request):
    # A GET request only displays the staff registration page.
    if request.method == "GET":
        return render(request, "core/organization_signup.html")

    # Read values submitted by the staff registration form.
    first_name = request.POST.get("firstName", "").strip()
    last_name = request.POST.get("lastName", "").strip()
    username = request.POST.get("username", "").strip().lower()
    email = request.POST.get("email", "").strip().lower()

    organization = request.POST.get("organization", "").strip()
    phone = request.POST.get("phone", "").strip()
    facility_type = request.POST.get("facilityType", "")

    street_address = request.POST.get("fullAddress", "").strip()
    city = request.POST.get("city", "").strip()
    province = request.POST.get("Province", "").strip()
    country = request.POST.get("country", "").strip()
    postal_code = request.POST.get("pincode", "").strip()

    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirmPassword", "")

    authorized_staff = request.POST.get("authorizedStaff")
    terms_accepted = request.POST.get("terms")

    # Preserve non-sensitive information if validation fails.
    # Passwords are deliberately excluded.
    form_data = {
        "firstName": first_name,
        "lastName": last_name,
        "username": username,
        "email": email,
        "organization": organization,
        "phone": phone,
        "facilityType": facility_type,
        "fullAddress": street_address,
        "city": city,
        "Province": province,
        "country": country,
        "pincode": postal_code,
        "authorizedStaff": bool(authorized_staff),
        "terms": bool(terms_accepted),
    }

    # Staff usernames must follow the ST prefix convention used by the frontend.
    if not username.startswith("st"):
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "Staff usernames must begin with 'st'.",
                "form_data": form_data,
            },
        )

    if password != confirm_password:
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "Passwords do not match.",
                "form_data": form_data,
            },
        )

    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "That username is already in use.",
                "form_data": form_data,
            },
        )

    if Users.objects.filter(email=email).exists():
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "An account with that email already exists.",
                "form_data": form_data,
            },
        )

    if not authorized_staff:
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "You must confirm that you are an authorized staff member.",
                "form_data": form_data,
            },
        )

    if not terms_accepted:
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "You must accept the terms and privacy policy.",
                "form_data": form_data,
            },
        )

    # Convert the wording used in the HTML dropdown into the exact
    # values allowed by the PostgreSQL database.
    facility_type_mapping = {
        "Hospital": "HOSPITAL",
        "Blood Bank": "BLOOD_BANK",
    }

    database_facility_type = facility_type_mapping.get(facility_type)

    if database_facility_type is None:
        return render(
            request,
            "core/organization_signup.html",
            {
                "error": "Please select a valid facility type.",
                "form_data": form_data,
            },
        )

    now = timezone.now()

    # User, facility and staff profile creation are treated as one operation.
    # If any step fails, the database transaction is rolled back.
    with transaction.atomic():
        user = Users.objects.create(
            username=username,
            email=email,
            password_hash=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role="HOSPITAL_STAFF",
            account_status="ACTIVE",
            terms_accepted_at=now,
            created_at=now,
            updated_at=now,
        )

        # If this facility is already registered, reuse it rather than
        # creating duplicate facility records.
        facility, created = Facilities.objects.get_or_create(
            name=organization,
            postal_code=postal_code,
            defaults={
                "facility_type": database_facility_type,
                "phone": phone,
                "country": country,
                "street_address": street_address,
                "city": city,
                "province": province,
                "created_at": now,
            },
        )

        StaffProfiles.objects.create(
            user=user,
            facility=facility,
            authorization_status="PENDING",
            authorization_declared_at=now,
        )

    return redirect("login")