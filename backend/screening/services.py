from django.db import IntegrityError
from django.utils import timezone

from .models import EligibilityScreenings


def get_or_create_emergency_screening(request_match):
    """
    Return the active emergency screening for a RequestMatch.

    If no IN_PROGRESS screening exists, create one.

    A RequestMatch identifies:
        - the emergency request
        - the matched donor

    The screening result is preliminary only and must be
    completed before the donor can proceed with the
    emergency donation response.
    """

    if request_match is None:
        return None

    donor = getattr(request_match, "donor", None)

    if donor is None:
        return None

    existing_screening = (
        EligibilityScreenings.objects
        .filter(
            request_match=request_match,
            screening_type="EMERGENCY",
            status="IN_PROGRESS",
        )
        .order_by("-started_at")
        .first()
    )

    if existing_screening:
        return existing_screening

    try:
        screening = EligibilityScreenings.objects.create(
            donor=donor,
            request_match=request_match,
            screening_type="EMERGENCY",
            appointment=None,
            status="IN_PROGRESS",
            preliminary_result="PENDING",
            rules_version="V1",
            started_at=timezone.now(),
            completed_at=None,
            valid_until=None,
        )

    except IntegrityError:
        # Handles two processes attempting to create the
        # same active screening at nearly the same time.
        screening = (
            EligibilityScreenings.objects
            .filter(
                request_match=request_match,
                screening_type="EMERGENCY",
                status="IN_PROGRESS",
            )
            .order_by("-started_at")
            .first()
        )

    return screening

def evaluate_emergency_screening(answers_by_code):
    """
    Evaluate emergency pre-screening answers.

    This is preliminary triage only.
    Final donation eligibility must be determined by
    qualified healthcare staff.

    Returns:
        preliminary_result
        flagged_answers
    """

    flagged_answers = {}

    # -----------------------------------------------------
    # RULE 1:
    # A donor who reports that they are not feeling well
    # should not proceed with the emergency donation flow.
    # -----------------------------------------------------
    if answers_by_code.get("FEELING_WELL") != "true":
        flagged_answers["FEELING_WELL"] = (
            "Donor reported that they are not feeling well today."
        )

        return (
            "TEMPORARILY_INELIGIBLE",
            flagged_answers,
        )

    # -----------------------------------------------------
    # RULE 2:
    # These answers require additional staff review.
    # They do NOT automatically mean the donor is medically
    # ineligible.
    # -----------------------------------------------------
    review_rules = {
        "RECENT_DONATION": (
            "Recent donation requires additional eligibility review."
        ),
        "RECENT_TRAVEL": (
            "Recent travel requires additional eligibility review."
        ),
        "RECENT_PROCEDURE": (
            "Recent medical or dental procedure requires "
            "additional eligibility review."
        ),
    }

    for question_code, flag_reason in review_rules.items():
        if answers_by_code.get(question_code) == "true":
            flagged_answers[question_code] = flag_reason

    # -----------------------------------------------------
    # RULE 3:
    # If the donor voluntarily provides additional
    # information, staff should review it before proceeding.
    # -----------------------------------------------------
    additional_information = (
        answers_by_code
        .get("ADDITIONAL_INFORMATION", "")
        .strip()
    )

    if additional_information:
        flagged_answers["ADDITIONAL_INFORMATION"] = (
            "Donor provided additional information for staff review."
        )

    # -----------------------------------------------------
    # FINAL PRELIMINARY RESULT
    # -----------------------------------------------------
    if flagged_answers:
        return (
            "REVIEW_REQUIRED",
            flagged_answers,
        )

    return (
        "PRELIMINARY_ELIGIBLE",
        flagged_answers,
    )