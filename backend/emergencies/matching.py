import logging

from math import asin, cos, radians, sin, sqrt
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from core.models import DonorProfiles
from .models import RequestMatches
from screening.services import get_or_create_emergency_screening
from .observer import (
    DonorNotificationListener,
    EmergencyBroadcastManager,
)

logger = logging.getLogger(__name__)

# Blood/component compatibility rules used by the
# LifeLine emergency donor matching system.


ALL_BLOOD_TYPES = {
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
}


# Compatible donor types for red blood cells / whole blood.
RED_CELL_COMPATIBILITY = {
    "A+": {"A+", "A-", "O+", "O-"},
    "A-": {"A-", "O-"},
    "B+": {"B+", "B-", "O+", "O-"},
    "B-": {"B-", "O-"},
    "AB+": ALL_BLOOD_TYPES,
    "AB-": {"AB-", "A-", "B-", "O-"},
    "O+": {"O+", "O-"},
    "O-": {"O-"},
}


# Plasma compatibility works differently from red cells.
PLASMA_COMPATIBILITY = {
    "A+": {"A+", "A-", "AB+", "AB-"},
    "A-": {"A+", "A-", "AB+", "AB-"},
    "B+": {"B+", "B-", "AB+", "AB-"},
    "B-": {"B+", "B-", "AB+", "AB-"},
    "AB+": {"AB+", "AB-"},
    "AB-": {"AB+", "AB-"},
    "O+": ALL_BLOOD_TYPES,
    "O-": ALL_BLOOD_TYPES,
}


def get_compatible_donor_blood_types(
    required_blood_type,
    component_type,
):
    """
    Return the donor blood types compatible with an
    emergency request.
    """

    required_blood_type = (
        required_blood_type or ""
    ).strip().upper()

    component_type = (
        component_type or ""
    ).strip().upper()

    # Staff may explicitly request any compatible donor.
    if required_blood_type == "ANY":
        return ALL_BLOOD_TYPES.copy()

    if required_blood_type not in ALL_BLOOD_TYPES:
        return set()

    if component_type in {
        "WHOLE_BLOOD",
        "RED_BLOOD_CELLS",
    }:
        return RED_CELL_COMPATIBILITY.get(
            required_blood_type,
            set(),
        )

    if component_type == "PLASMA":
        return PLASMA_COMPATIBILITY.get(
            required_blood_type,
            set(),
        )

    if component_type == "PLATELETS":
        # Platelet ABO compatibility is more flexible.
        # We allow all ABO groups here and will later
        # prioritize closer/exact matches using match score.
        return ALL_BLOOD_TYPES.copy()

    return set()


def is_blood_compatible(
    donor_blood_type,
    required_blood_type,
    component_type,
):
    """
    Return True when the donor blood type is compatible
    with the emergency request.
    """

    donor_blood_type = (
        donor_blood_type or ""
    ).strip().upper()

    compatible_types = get_compatible_donor_blood_types(
        required_blood_type,
        component_type,
    )

    return donor_blood_type in compatible_types

def calculate_distance_km(
    origin_latitude,
    origin_longitude,
    destination_latitude,
    destination_longitude,
):
    """
    Calculate the straight-line distance in kilometres
    between two latitude/longitude coordinates using
    the Haversine formula.

    Returns None when any coordinate is missing or invalid.
    """

    coordinates = (
        origin_latitude,
        origin_longitude,
        destination_latitude,
        destination_longitude,
    )

    if any(value is None for value in coordinates):
        return None

    try:
        origin_latitude = float(origin_latitude)
        origin_longitude = float(origin_longitude)
        destination_latitude = float(destination_latitude)
        destination_longitude = float(destination_longitude)

    except (TypeError, ValueError):
        return None

    # Reject impossible coordinates instead of allowing
    # corrupted location data into the matching process.
    if not (
        -90 <= origin_latitude <= 90
        and -90 <= destination_latitude <= 90
        and -180 <= origin_longitude <= 180
        and -180 <= destination_longitude <= 180
    ):
        return None

    earth_radius_km = 6371.0088

    latitude_difference = radians(
        destination_latitude - origin_latitude
    )

    longitude_difference = radians(
        destination_longitude - origin_longitude
    )

    origin_latitude = radians(origin_latitude)
    destination_latitude = radians(destination_latitude)

    haversine_value = (
        sin(latitude_difference / 2) ** 2
        + cos(origin_latitude)
        * cos(destination_latitude)
        * sin(longitude_difference / 2) ** 2
    )

    # Floating-point rounding can very rarely push the
    # Haversine value slightly outside the valid 0-1 range.
    haversine_value = max(
        0.0,
        min(1.0, haversine_value),
    )

    angular_distance = 2 * asin(
        sqrt(haversine_value)
    )

    return earth_radius_km * angular_distance

def is_donor_eligible_for_emergency(
    donor,
    today=None,
):
    """
    Return True when a donor is currently eligible
    to participate in emergency matching.

    This checks the eligibility information that
    currently exists in the donor profile.
    """

    if donor is None:
        return False

    # Donor must have emergency participation enabled.
    if not donor.emergency_available:
        return False

    # The associated account must be an active donor account.
    user = getattr(donor, "user", None)

    if user is None:
        return False

    if user.role != "DONOR":
        return False

    if user.account_status != "ACTIVE":
        return False

    if today is None:
        today = timezone.localdate()

    # A NULL next_eligible_date means there is currently
    # no stored future restriction on donation.
    if (
        donor.next_eligible_date is not None
        and donor.next_eligible_date > today
    ):
        return False

    return True

def calculate_match_score(
    donor_blood_type,
    required_blood_type,
    component_type,
    distance_km,
    radius_km,
):
    """
    Calculate a ranking score for an eligible,
    compatible emergency donor.

    Higher scores are better.

    Blood compatibility contributes up to 70 points.
    Geographic proximity contributes up to 30 points.
    """

    if distance_km is None or radius_km is None:
        return None

    try:
        distance_km = Decimal(str(distance_km))
        radius_km = Decimal(str(radius_km))

    except Exception:
        return None

    if radius_km <= 0 or distance_km < 0:
        return None

    if distance_km > radius_km:
        return None

    donor_blood_type = (
        donor_blood_type or ""
    ).strip().upper()

    required_blood_type = (
        required_blood_type or ""
    ).strip().upper()

    component_type = (
        component_type or ""
    ).strip().upper()

    # Donor must actually be compatible before scoring.
    if not is_blood_compatible(
        donor_blood_type,
        required_blood_type,
        component_type,
    ):
        return None

    # Exact blood-group matches are preferred.
    if (
        required_blood_type != "ANY"
        and donor_blood_type == required_blood_type
    ):
        blood_score = Decimal("70")

    else:
        # Compatible donor, but not an exact blood-group match.
        blood_score = Decimal("55")

    # Closer donors receive more proximity points.
    distance_ratio = distance_km / radius_km

    proximity_score = (
        Decimal("30")
        * (Decimal("1") - distance_ratio)
    )

    if proximity_score < 0:
        proximity_score = Decimal("0")

    total_score = blood_score + proximity_score

    return total_score.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

def create_candidate_matches(emergency_request):
    """
    Find compatible emergency donor candidates and create
    RequestMatches rows for them.

    These are preliminary candidate matches only.
    Medical screening has NOT been completed at this stage.
    """

    if emergency_request is None:
        return []

    facility = getattr(emergency_request, "facility", None)

    if facility is None:
        return []

    # Matching by radius requires coordinates for the
    # requesting hospital/blood bank.
    if (
        facility.latitude is None
        or facility.longitude is None
    ):
        return []

    compatible_blood_types = get_compatible_donor_blood_types(
        emergency_request.required_blood_type,
        emergency_request.component_type,
    )

    if not compatible_blood_types:
        return []

    # Reduce the candidate pool in PostgreSQL first.
    donors = (
        DonorProfiles.objects
        .select_related("user")
        .filter(
            emergency_available=True,
            blood_type__in=compatible_blood_types,
            latitude__isnull=False,
            longitude__isnull=False,
            user__role="DONOR",
            user__account_status="ACTIVE",
        )
    )

    matched_rows = []
    matched_at = timezone.now()

    for donor in donors:

        # Profile-level eligibility gate.
        if not is_donor_eligible_for_emergency(donor):
            continue

        distance_km = calculate_distance_km(
            facility.latitude,
            facility.longitude,
            donor.latitude,
            donor.longitude,
        )

        if distance_km is None:
            continue

        try:
            request_radius_km = float(
                emergency_request.radius_km
            )
        except (TypeError, ValueError):
            continue

        # Donor must be inside the hospital-selected radius.
        if distance_km > request_radius_km:
            continue

        match_score = calculate_match_score(
            donor.blood_type,
            emergency_request.required_blood_type,
            emergency_request.component_type,
            distance_km,
            emergency_request.radius_km,
        )

        if match_score is None:
            continue

        distance_decimal = Decimal(
            str(distance_km)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # The database has a unique request + donor rule.
        # get_or_create makes repeated matching safe.
        request_match, created = (
            RequestMatches.objects.get_or_create(
                request=emergency_request,
                donor=donor,
                defaults={
                    "distance_km": distance_decimal,
                    "match_score": match_score,
                    "notification_status": "PENDING",
                    "response_status": "PENDING",
                    "matched_at": matched_at,
                },

            )
        )

        # Every emergency candidate must have a screening
        # session before they can proceed with the donation.
        get_or_create_emergency_screening(
            request_match
        )

        matched_rows.append(request_match)

    # Highest-ranked donors first.
    matched_rows.sort(
        key=lambda match: (
            match.match_score
            if match.match_score is not None
            else Decimal("-1")
        ),
        reverse=True,
    )

    return matched_rows


def run_emergency_matching(emergency_request):
    """
    Run donor matching for an emergency request.

    Status flow:
        OPEN -> MATCHING
        MATCHING -> ACTIVE when candidates are found
        MATCHING -> OPEN when no candidates are found

    If matching fails unexpectedly, return the request
    to OPEN so it is not left stuck in MATCHING.
    """

    if emergency_request is None:
        return []

    emergency_request.status = "MATCHING"
    emergency_request.updated_at = timezone.now()

    emergency_request.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    try:
        matched_rows = create_candidate_matches(
            emergency_request
        )

    except Exception:
        emergency_request.status = "OPEN"
        emergency_request.updated_at = timezone.now()

        emergency_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise

    emergency_request.status = "ACTIVE"

    emergency_request.updated_at = timezone.now()

    emergency_request.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    # ---------------------------------------------------------
    # SELECT + DISPATCH INITIAL NOTIFICATION WAVE
    # ---------------------------------------------------------
    if matched_rows:

        initial_wave = select_initial_notification_wave(
            emergency_request,
            matched_rows,
        )

        try:
            # -----------------------------------------------------
            # OBSERVER PATTERN
            #
            # EmergencyBroadcastManager = Subject
            # DonorNotificationListener = Concrete Observer
            # -----------------------------------------------------
            broadcast_manager = (
                EmergencyBroadcastManager()
            )

            donor_notification_listener = (
                DonorNotificationListener()
            )

            broadcast_manager.attach(
                donor_notification_listener
            )

            observer_results = (
                broadcast_manager.notify(
                    emergency_request,
                    initial_wave,
                )
            )

            logger.info(
                "Emergency %s initial notification "
                "wave observer results: %s",
                emergency_request.id,
                observer_results,
            )

        except Exception:
            # A notification-system failure must never delete
            # the emergency request or matching results.
            logger.exception(
                "Initial emergency broadcast failed "
                "for emergency request %s.",
                emergency_request.id,
            )

    return matched_rows


def select_initial_notification_wave(
    emergency_request,
    matched_rows,
):
    """
    Select the highest-ranked donors for the first
    emergency notification wave.

    All compatible candidates remain stored in
    RequestMatches, but only a smaller group is
    contacted initially.

    Initial wave size:
        max(5, units_required * 2)
    """

    if emergency_request is None:
        return []

    if not matched_rows:
        return []

    try:
        units_required = int(
            emergency_request.units_required
        )
    except (TypeError, ValueError):
        return []

    if units_required <= 0:
        return []

    # Contact at least five donors, or roughly twice
    # the number of requested units.
    initial_group_size = max(
        5,
        units_required * 2,
    )

    # Only donors who have not already been contacted
    # or responded can enter a new notification wave.
    available_matches = [
        request_match
        for request_match in matched_rows
        if (
            request_match.notification_status == "PENDING"
            and request_match.response_status == "PENDING"
        )
    ]

    # Highest matching score first.
    available_matches.sort(
        key=lambda request_match: (
            request_match.match_score
            if request_match.match_score is not None
            else Decimal("-1")
        ),
        reverse=True,
    )

    return available_matches[
        :initial_group_size
    ]