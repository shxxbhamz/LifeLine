from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import DonorProfiles, Users


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
    return render(request, "core/organization_signup.html")