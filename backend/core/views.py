import uuid
import logging
from django.http import HttpResponseServerError
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from core.models import DonorProfiles
from .models import DonorProfiles, Facilities, StaffProfiles, Users
from appointments.models import Appointments
from inventory.models import BloodInventory
from emergencies.models import EmergencyRequests
from .geocoding import geocode_address
logger = logging.getLogger(__name__)
from .utils import send_welcome_email

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

#Heer Patel#
def donor_dashboard_view(request):
    # 1. Check custom session authentication
    if (
        request.session.get("user_id") is None
        or request.session.get("role") != "DONOR"
    ):
        return redirect("login")

    user_id = request.session.get("user_id")

    donor_profile = None
    upcoming_appointment = None
    days_left = None

    total_donations = 0
    lives_saved = 0

    tier_name = "Welcome Donor"
    next_goal = 1
    progress_percent = 0

    # Default achievement values
    welcome_unlocked = False
    dedicated_unlocked = False
    life_saver_unlocked = False
    hero_unlocked = False

    dedicated_remaining = 30
    life_saver_remaining = 60
    hero_remaining = 90

    try:
        donor_profile = DonorProfiles.objects.get(user_id=user_id)

        # 2. Count ALL completed donations (including emergency fulfillments & regular appointments)
        total_donations = Appointments.objects.filter(
            donor_id=user_id,
            status__iexact="COMPLETED"
        ).count()

        lives_saved = total_donations

        # 3. Calculate donor tier and progress
        if total_donations == 0:
            tier_name = "Welcome Donor"
            next_goal = 1
            progress_percent = 0

        elif total_donations < 30:
            tier_name = "Dedicated Donor Tier"
            next_goal = 30
            progress_percent = (total_donations / 30) * 100

        elif total_donations < 60:
            tier_name = "Life Saver Tier"
            next_goal = 60
            progress_percent = (total_donations / 60) * 100

        elif total_donations < 90:
            tier_name = "Hero Tier"
            next_goal = 90
            progress_percent = (total_donations / 90) * 100

        else:
            tier_name = "Elite Legend Tier"
            next_goal = total_donations + 10
            progress_percent = 100

        # 4. Calculate achievement badge activation
        welcome_unlocked = total_donations >= 1
        dedicated_unlocked = total_donations >= 30
        life_saver_unlocked = total_donations >= 60
        hero_unlocked = total_donations >= 90

        # 5. Calculate remaining donations for each badge
        dedicated_remaining = max(30 - total_donations, 0)
        life_saver_remaining = max(60 - total_donations, 0)
        hero_remaining = max(90 - total_donations, 0)

        # 6. Find the next upcoming appointment
        now = timezone.now()

        upcoming_appointment = Appointments.objects.filter(
            donor=donor_profile,
            scheduled_at__gte=now
        ).exclude(
            status__iexact="CANCELLED"
        ).order_by("scheduled_at").first()

        # 7. Calculate days remaining
        if upcoming_appointment:
            delta = upcoming_appointment.scheduled_at.date() - now.date()
            days_left = delta.days

    except DonorProfiles.DoesNotExist:
        pass

    # 8. Prepare dashboard context
    context = {
        "donor_profile": donor_profile,
        "upcoming_appointment": upcoming_appointment,
        "days_left": days_left,

        # Donation statistics
        "total_donations": total_donations,
        "lives_saved": lives_saved,

        # Donor tier and progress
        "tier_name": tier_name,
        "next_goal": next_goal,
        "progress_percent": round(progress_percent, 2),

        # Achievement badge activation
        "welcome_unlocked": welcome_unlocked,
        "dedicated_unlocked": dedicated_unlocked,
        "life_saver_unlocked": life_saver_unlocked,
        "hero_unlocked": hero_unlocked,

        # Remaining donations
        "dedicated_remaining": dedicated_remaining,
        "life_saver_remaining": life_saver_remaining,
        "hero_remaining": hero_remaining,
    }

    return render(request, "donor/index.html", context)


    def donor_active_requests_view(request):
    if request.session.get("user_id") is None or request.session.get("role") != "DONOR":
        return redirect("login")

    user_id = request.session.get("user_id")
    emergency_requests = []

    try:
        donor_profile = DonorProfiles.objects.get(user_id=user_id)
        donor_blood_type = donor_profile.blood_type

        # Fetch active emergency requests matching the donor's blood type
        # Adjust table/model names (EmergencyRequests, facility) to match your project structure
        emergency_requests = EmergencyRequests.objects.filter(
            blood_group__iexact=donor_blood_type,
            status__iexact='ACTIVE'  # or whatever field tracks active state
        ).select_related('facility').order_by('-created_at')

    except DonorProfiles.DoesNotExist:
        pass

    context = {
        'emergency_requests': emergency_requests,
    }
    return render(request, "donor/active_requests.html", context)
    #Heer Patel#


def staff_dashboard_view(request):
    # 1. Check custom staff login session
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    if user_id is None or user_role != "HOSPITAL_STAFF":
        return redirect("login")

    # 2. Default values
    facility_name = "Organization Staff Console"
    facility_type = "hospital"
    current_user = None
    current_facility_id = None

    scheduled_appointments = []
    inventory_items = []
    emergency_history = []
    map_facilities = []

    try:
        # 3. Get logged-in user
        current_user = Users.objects.get(id=user_id)

        # 4. Get staff profile and associated facility
        staff_profile = StaffProfiles.objects.select_related(
            "facility"
        ).get(user_id=user_id)

        facility = staff_profile.facility

        if facility:
            current_facility_id = facility.id
            facility_name = facility.name

            if facility.facility_type:
                facility_type = facility.facility_type.lower()

            # 5. Get appointments for this facility
            scheduled_appointments = list(
                Appointments.objects.filter(
                    facility=facility
                ).select_related("donor__user")
            )

            # 6. Get blood inventory
            raw_inventory = BloodInventory.objects.filter(
                facility=facility
            )

            inventory_dict = {}

            for inv in raw_inventory:
                blood_type = inv.blood_type

                if blood_type not in inventory_dict:
                    inventory_dict[blood_type] = {
                        "blood_type": blood_type,
                        "whole_blood": 0,
                        "plasma": 0,
                        "status": "Normal",
                    }

                component = str(inv.component_type).lower()
                units = inv.units_available or 0

                if "whole" in component:
                    inventory_dict[blood_type]["whole_blood"] += units

                elif "plasma" in component:
                    inventory_dict[blood_type]["plasma"] += units

                # Inventory threshold checks
                if (
                    inv.critical_threshold is not None
                    and units <= inv.critical_threshold
                ):
                    inventory_dict[blood_type]["status"] = "Critical"

                elif (
                    inv.low_threshold is not None
                    and units <= inv.low_threshold
                    and inventory_dict[blood_type]["status"] != "Critical"
                ):
                    inventory_dict[blood_type]["status"] = "Low"

            inventory_items = list(inventory_dict.values())

            # 7. Get emergency requests for this facility
            emergency_history = list(
                EmergencyRequests.objects.filter(
                    facility=facility
                ).order_by("-created_at")
            )

            # 8. Get facilities with map coordinates
            facilities_with_locations = Facilities.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
            )

            for item in facilities_with_locations:
                map_facilities.append({
                    "id": item.id,
                    "name": item.name,
                    "type": item.facility_type,
                    "address": (
                        f"{item.street_address or ''}, "
                        f"{item.city or ''}, "
                        f"{item.province or ''}, "
                        f"{item.postal_code or ''}"
                    ),
                    "latitude": float(item.latitude),
                    "longitude": float(item.longitude),
                })

    except Users.DoesNotExist:
        logger.warning(
            "Staff dashboard: user ID %s does not exist",
            user_id
        )
        request.session.flush()
        return redirect("login")

    except StaffProfiles.DoesNotExist:
        logger.warning(
            "Staff dashboard: staff profile missing for user ID %s",
            user_id
        )
        request.session.flush()
        return redirect("login")

    except Exception:
        logger.exception(
            "STAFF DASHBOARD ERROR while loading database records. User ID: %s",
            user_id
        )
        return HttpResponseServerError(
            "Staff dashboard failed. Please check application logs."
        )

    # 9. Prepare dashboard context
    context = {
        "facility_name": facility_name,
        "facility_type": facility_type,
        "logged_in_user": current_user,
        "scheduled_appointments": scheduled_appointments,
        "inventory_items": inventory_items,
        "emergency_history": emergency_history,
        "emergency_form_token": uuid.uuid4().hex,
        "map_facilities": map_facilities,
        "current_facility_id": current_facility_id,
    }

    # 10. Render dashboard with separate error logging
    try:
        return render(
            request,
            "organization/index.html",
            context
        )

    except Exception:
        logger.exception(
            "STAFF DASHBOARD TEMPLATE ERROR. User ID: %s",
            user_id
        )
        return HttpResponseServerError(
            "Staff dashboard template failed. Please check application logs."
        )


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
        "username": request.POST.get("username", "").strip().lower(),
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

    # Donor usernames must follow the 'do' prefix convention used by the frontend.
    if username.startswith("do"):
        username = username[2:]
    
    username = f"do{username}"  # Results in 'dopheerpatel' automatically

    # Check for duplicates using the final generated username
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

    # Convert the donor's registered address into geographic coordinates.
    # If geocoding fails, registration can still proceed without coordinates.
    coordinates = geocode_address(
        street_address,
        city,
        province,
        postal_code,
        country,
    )

    latitude = coordinates[0] if coordinates else None
    longitude = coordinates[1] if coordinates else None

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
            latitude=latitude,
            longitude=longitude,
        )

    # Automatically send the welcome email immediately after successful registration
    try:
        send_welcome_email(user_email=email, username=first_name, role="Donor")
    except Exception as e:
        print(f"Failed to send welcome email to donor: {e}")

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
    form_data = {
        "firstName": first_name,
        "lastName": last_name,
        "username": request.POST.get("username", "").strip().lower(),
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
    if username.startswith("st"):
        username = username[2:]
    
    username = f"st{username}"  # Results in 'st...' automatically

    # Check for duplicates using the final generated username
    if Users.objects.filter(username=username).exists():
        return render(
            request,
            "organization_signup.html",
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

    # Convert the organization's registered address into coordinates.
    # If geocoding fails, registration can still proceed.
    coordinates = geocode_address(
        street_address,
        city,
        province,
        postal_code,
        country,
    )

    latitude = coordinates[0] if coordinates else None
    longitude = coordinates[1] if coordinates else None

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
                "latitude": latitude,
                "longitude": longitude,
            },
        )

        StaffProfiles.objects.create(
            user=user,
            facility=facility,
            authorization_declared_at=now,
        )

    # Automatically send the welcome email based on facility type (Hospital vs Blood Bank)
    try:
        send_welcome_email(user_email=email, username=first_name, role=facility_type)
    except Exception as e:
        print(f"Failed to send welcome email to staff: {e}")

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

        # Only geocode again if the donor's address has changed.
        address_changed = (
            donor_profile.street_address != address
            or donor_profile.city != city
            or donor_profile.province != province
            or donor_profile.postal_code != postal_code
            or donor_profile.country != country
        )

        if address_changed:
            # Convert the updated address into new coordinates.
            coordinates = geocode_address(
                address,
                city,
                province,
                postal_code,
                country,
            )

            # Clear old coordinates if the new address cannot be located.
            donor_profile.latitude = coordinates[0] if coordinates else None
            donor_profile.longitude = coordinates[1] if coordinates else None

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

        # Check whether the facility's address has changed.
        address_changed = (
            facility.street_address != street_address
            or facility.city != city
            or facility.province != province
            or facility.postal_code != postal_code
            or facility.country != country
        )

        if address_changed:
            # Convert the updated address into new coordinates.
            coordinates = geocode_address(
                street_address,
                city,
                province,
                postal_code,
                country,
            )

            # Replace old coordinates or clear them if geocoding fails.
            facility.latitude = coordinates[0] if coordinates else None
            facility.longitude = coordinates[1] if coordinates else None

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