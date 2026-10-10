from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import DonorProfiles, Facilities, StaffProfiles, Users

def home_view(request):
    return render(request, "index.html")

def login_view(request):
    # A GET request only displays the login page.
    if request.method == "GET":
        return render(request, "login.html")

    username = request.POST.get("username", "").strip().lower()
    password = request.POST.get("password", "")

    # Preserve the username after a failed login attempt.
    form_data = {
        "username": username,
    }

    try:
        user = Users.objects.get(username=username)
    except Users.DoesNotExist:
        return render(
            request,
            "login.html",
            {
                "error": "Invalid username or password.",
                "form_data": form_data,
            },
        )

    # Compare the submitted password with the securely stored password hash.
    if not check_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            {
                "error": "Invalid username or password.",
                "form_data": form_data,
            },
        )

    # Prevent suspended accounts from signing in.
    if user.account_status != "ACTIVE":
        return render(
            request,
            "login.html",
            {
                "error": "This account is not currently active.",
                "form_data": form_data,
            },
        )

    # Store only the minimum information needed to identify the logged-in user.
    request.session["user_id"] = user.id
    request.session["role"] = user.role

    # Send each account type to its own dashboard.
    if user.role == "DONOR":
        return redirect("donor_dashboard")

    if user.role == "HOSPITAL_STAFF":
        return redirect("staff_dashboard")

    return render(
        request,
        "login.html",
        {
            "error": "This account has an unsupported role.",
            "form_data": form_data,
        },
    )

def donor_dashboard_view(request):
    # Only logged-in donors should be able to access the donor dashboard.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    return render(request, "donor/index.html")


def staff_dashboard_view(request):
    # Only logged-in staff should be able to access the staff dashboard.
    if request.session.get("user_id") is None or request.session.get("role") != "HOSPITAL_STAFF":
        return redirect("login")

    return render(request, "organization/index.html")

def logout_view(request):
    # Remove all authentication data stored in the current session.
    request.session.flush()

    return redirect("login")

def donor_signup_view(request):
    # A GET request only displays the registration page.
    if request.method == "GET":
        return render(request, "donor_signup.html")

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

   # 1. Get whatever username the user typed
    username = request.POST.get("username", "").strip().lower()

    # 2. Automatically prepend "do" if they didn't write it, 
    # but strip it first if they somehow typed it twice.
    if username.startswith("do"):
        username = username[2:]
    
    username = f"do{username}"  # Results in 'dopheerpatel' automatically

    form_data = {
        "firstName": first_name,
        "lastName": last_name,
        "username": request.POST.get("username", "").strip().lower(), # Keep what they typed in box
        # ... rest of your fields ...
    }

    # 3. Check for duplicates using the final generated username
    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "donor_signup.html",
            {"error": f"The username '{username}' is already in use.", "form_data": form_data},
        )

    if password != confirm_password:
        return render(
            request,
            "donor_signup.html",
            {"error": "Passwords do not match.", "form_data": form_data},
        )

    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "donor_signup.html",
            {"error": "That username is already in use.", "form_data": form_data},
        )

    if Users.objects.filter(email=email).exists():
        return render(
            request,
            "donor_signup.html",
            {"error": "An account with that email already exists.", "form_data": form_data},
        )

    if not terms_accepted:
        return render(
            request,
            "donor_signup.html",
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
        return render(request, "organization_signup.html")

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
    # 1. Get whatever username the user typed
    username = request.POST.get("username", "").strip().lower()

    # 2. Automatically prepend "do" if they didn't write it, 
    # but strip it first if they somehow typed it twice.
    if username.startswith("st"):
        username = username[2:]
    
    username = f"do{username}"  # Results in 'dopheerpatel' automatically

    form_data = {
        "firstName": first_name,
        "lastName": last_name,
        "username": request.POST.get("username", "").strip().lower(), # Keep what they typed in box
        # ... rest of your fields ...
    }

    # 3. Check for duplicates using the final generated username
    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "donor_signup.html",
            {"error": f"The username '{username}' is already in use.", "form_data": form_data},
        )

    if password != confirm_password:
        return render(
            request,
            "organization_signup.html",
            {
                "error": "Passwords do not match.",
                "form_data": form_data,
            },
        )

    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "organization_signup.html",
            {
                "error": "That username is already in use.",
                "form_data": form_data,
            },
        )

    if Users.objects.filter(email=email).exists():
        return render(
            request,
            "organization_signup.html",
            {
                "error": "An account with that email already exists.",
                "form_data": form_data,
            },
        )

    if not authorized_staff:
        return render(
            request,
            "organization_signup.html",
            {
                "error": "You must confirm that you are an authorized staff member.",
                "form_data": form_data,
            },
        )

    if not terms_accepted:
        return render(
            request,
            "organization_signup.html",
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
            "organization_signup.html",
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

def donor_edit_profile_view(request):
    # Only logged-in donors can access this page.
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    user_id = request.session["user_id"]

    try:
        user = Users.objects.get(id=user_id)
        donor_profile = DonorProfiles.objects.get(user_id=user_id)
    except (Users.DoesNotExist, DonorProfiles.DoesNotExist):
        request.session.flush()
        return redirect("login")

    if request.method == "POST":
        first_name = request.POST.get("firstName", "").strip()
        last_name = request.POST.get("lastName", "").strip()
        username = request.POST.get("username", "").strip().lower()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        dob = request.POST.get("dob", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        province = request.POST.get("province", "").strip()
        country = request.POST.get("country", "").strip()
        postal_code = request.POST.get("postalCode", "").strip()
        blood_type = request.POST.get("bloodGroup", "").strip()


        # Donor usernames must continue to follow the 'do...' convention.
        if not username.startswith("do"):
            return render(
                request,
                "donor/edit_dor_profile.html",
                {
                    "user": user,
                    "donor_profile": donor_profile,
                    "form_data": request.POST,
                    "error": "Donor usernames must start with 'do'.",
                },
            )

        # Allow the donor to keep their own username, but block one
        # that already belongs to another account.
        if Users.objects.exclude(id=user_id).filter(username=username).exists():
            return render(
                request,
                "donor/edit_dor_profile.html",
                {
                    "user": user,
                    "donor_profile": donor_profile,
                    "form_data": request.POST,
                    "error": "That username is already in use.",
                },
            )

        # The same rule applies to email addresses.
        if Users.objects.exclude(id=user_id).filter(email=email).exists():
            return render(
                request,
                "donor/edit_dor_profile.html",
                {
                    "user": user,
                    "donor_profile": donor_profile,
                    "form_data": request.POST,
                    "error": "That email address is already in use.",
                },
            )


        # Update account information.
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email
        user.updated_at = timezone.now()

        # Update donor-specific profile information.
        donor_profile.phone = phone
        donor_profile.date_of_birth = dob
        donor_profile.street_address = address
        donor_profile.city = city
        donor_profile.province = province
        donor_profile.country = country
        donor_profile.postal_code = postal_code
        donor_profile.blood_type = blood_type

        # Save both records as one database transaction.
        with transaction.atomic():
            user.save()
            donor_profile.save()

        return redirect("donor_edit_profile")

    return render(
        request,
        "donor/edit_dor_profile.html",
        {
            "user": user,
            "donor_profile": donor_profile,
        },
    )

def staff_edit_profile_view(request):
    # Only logged-in staff can access this page.
    if request.session.get("user_id") is None or request.session.get("role") != "HOSPITAL_STAFF":
        return redirect("login")

    user_id = request.session["user_id"]

    # Load the staff account, staff profile and associated facility.
    try:
        user = Users.objects.get(id=user_id)
        staff_profile = StaffProfiles.objects.get(user_id=user_id)
        facility = staff_profile.facility
    except (Users.DoesNotExist, StaffProfiles.DoesNotExist):
        request.session.flush()
        return redirect("login")

    if request.method == "POST":
        # Read the editable values submitted by the form.
        first_name = request.POST.get("firstName", "").strip()
        last_name = request.POST.get("lastName", "").strip()
        email = request.POST.get("email", "").strip().lower()

        organization = request.POST.get("organization", "").strip()
        phone = request.POST.get("phone", "").strip()
        facility_type = request.POST.get("facilityType", "")

        street_address = request.POST.get("fullAddress", "").strip()
        city = request.POST.get("city", "").strip()
        province = request.POST.get("Province", "").strip()
        country = request.POST.get("country", "").strip()
        postal_code = request.POST.get("pincode", "").strip()

        # Allow the staff member to keep their current email, but prevent
        # an email address that already belongs to another account.
        if Users.objects.exclude(id=user_id).filter(email=email).exists():
            return render(
                request,
                "organization/edit_org_profile.html",
                {
                    "user": user,
                    "staff_profile": staff_profile,
                    "facility": facility,
                    "form_data": request.POST,
                    "error": "That email address is already in use.",
                },
            )

        # Convert the wording used by the frontend dropdown into the
        # values stored in PostgreSQL.
        facility_type_mapping = {
            "Hospital": "HOSPITAL",
            "Blood Bank": "BLOOD_BANK",
        }

        database_facility_type = facility_type_mapping.get(facility_type)

        if database_facility_type is None:
            return render(
                request,
                "organization/edit_org_profile.html",
                {
                    "user": user,
                    "staff_profile": staff_profile,
                    "facility": facility,
                    "form_data": request.POST,
                    "error": "Please select a valid facility type.",
                },
            )

        # A facility is uniquely identified by its name and postal code.
        # Prevent this facility from being changed into a duplicate of
        # another facility that already exists.
        if Facilities.objects.exclude(id=facility.id).filter(
            name=organization,
            postal_code=postal_code,
        ).exists():
            return render(
                request,
                "organization/edit_org_profile.html",
                {
                    "user": user,
                    "staff_profile": staff_profile,
                    "facility": facility,
                    "form_data": request.POST,
                    "error": "A facility with that name and postal code already exists.",
                },
            )

        # Update account information.
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.updated_at = timezone.now()

        # Update the associated facility information.
        facility.name = organization
        facility.phone = phone
        facility.facility_type = database_facility_type
        facility.street_address = street_address
        facility.city = city
        facility.province = province
        facility.country = country
        facility.postal_code = postal_code

        # Save the account and facility changes as one database transaction.
        with transaction.atomic():
            user.save()
            facility.save()

        return redirect("staff_edit_profile")

    # A GET request displays the staff member's existing information.
    return render(
        request,
        "organization/edit_org_profile.html",
        {
            "user": user,
            "staff_profile": staff_profile,
            "facility": facility,
        },
    )