from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from emergencies.models import (
    Notifications,
    RequestMatches,
)

from .models import (
    EligibilityScreenings,
    ScreeningAnswers,
    ScreeningQuestions,
)
from .services import (
    evaluate_emergency_screening,
    get_or_create_emergency_screening,
)
from .tokens import decode_emergency_screening_token


def emergency_screening_view(request, token):
    # ---------------------------------------------------------
    # 1. VALIDATE SECURE EMAIL TOKEN
    # ---------------------------------------------------------
    token_payload = decode_emergency_screening_token(token)

    if token_payload is None:
        return HttpResponseBadRequest(
            "This emergency screening link is invalid or has expired."
        )

    match_id = token_payload.get("match_id")
    donor_id = token_payload.get("donor_id")

    # ---------------------------------------------------------
    # 2. LOAD THE EXACT DONOR MATCH
    # ---------------------------------------------------------
    request_match = get_object_or_404(
        RequestMatches.objects.select_related(
            "request",
            "request__facility",
            "donor",
            "donor__user",
        ),
        id=match_id,
        donor_id=donor_id,
    )

    # Emergency must still be active and within its
    # configured expiration time.
    emergency_request = request_match.request

    if (
        emergency_request.status != "ACTIVE"
        or (
            emergency_request.expires_at is not None
            and emergency_request.expires_at
            <= timezone.now()
        )
    ):
        return HttpResponseBadRequest(
            "This emergency request is no longer active."
        )

    # An individual donor match may also expire even while
    # the parent emergency record still exists.
    if request_match.response_status == "EXPIRED":
        return HttpResponseBadRequest(
            "This emergency donor match has expired."
        )

    # ---------------------------------------------------------
    # MARK EMERGENCY NOTIFICATION AS VIEWED
    # ---------------------------------------------------------
    if request_match.notification_status == "SENT":
        viewed_at = timezone.now()

        request_match.notification_status = "VIEWED"
        request_match.viewed_at = viewed_at

        request_match.save(
            update_fields=[
                "notification_status",
                "viewed_at",
            ]
        )

        Notifications.objects.filter(
            request_match=request_match,
            notification_type="EMERGENCY_ALERT",
            is_read=False,
        ).update(
            is_read=True,
            read_at=viewed_at,
        )

    # Donor must not have already accepted/declined.
    if request_match.response_status in (
        "ACCEPTED",
        "DECLINED",
    ):
        completed_screening = (
            EligibilityScreenings.objects
            .filter(
                request_match=request_match,
                screening_type="EMERGENCY",
                status="COMPLETED",
            )
            .order_by("-completed_at")
            .first()
        )

        context = {
            "request_match": request_match,
            "emergency_request": request_match.request,
            "facility": request_match.request.facility,
            "screening": completed_screening,
            "questions": [],
            "screening_completed": bool(completed_screening),
            "preliminary_result": (
                completed_screening.preliminary_result
                if completed_screening
                else None
            ),
            "response_recorded": True,
            "response_status": request_match.response_status,
            "access_token": token,
        }

        return render(
            request,
            "donor/emergency_screening.html",
            context,
        )

    # ---------------------------------------------------------
    # 3. PREVENT A SECOND SCREENING FOR THE SAME MATCH
    # ---------------------------------------------------------
    completed_screening = (
        EligibilityScreenings.objects
        .filter(
            request_match=request_match,
            screening_type="EMERGENCY",
            status="COMPLETED",
        )
        .order_by("-completed_at")
        .first()
    )

    if completed_screening:
        context = {
            "request_match": request_match,
            "emergency_request": request_match.request,
            "facility": request_match.request.facility,
            "screening": completed_screening,
            "questions": [],
            "screening_completed": True,
            "preliminary_result": completed_screening.preliminary_result,
            "access_token": token,
        }

        return render(
            request,
            "donor/emergency_screening.html",
            context,
        )

    # ---------------------------------------------------------
    # 4. GET OR CREATE ACTIVE SCREENING SESSION
    # ---------------------------------------------------------
    screening = get_or_create_emergency_screening(
        request_match
    )

    if screening is None:
        return HttpResponseBadRequest(
            "The emergency screening could not be started."
        )

    questions = list(
        ScreeningQuestions.objects
        .filter(is_active=True)
        .order_by(
            "display_order",
            "id",
        )
    )

    if not questions:
        return HttpResponseBadRequest(
            "Screening questions are currently unavailable."
        )

    # ---------------------------------------------------------
    # 5. GET REQUEST - SHOW FORM
    # ---------------------------------------------------------
    if request.method == "GET":
        context = {
            "request_match": request_match,
            "emergency_request": request_match.request,
            "facility": request_match.request.facility,
            "screening": screening,
            "questions": questions,
            "access_token": token,
        }

        return render(
            request,
            "donor/emergency_screening.html",
            context,
        )

    # ---------------------------------------------------------
    # 6. POST REQUEST - VALIDATE ANSWERS
    # ---------------------------------------------------------
    normalized_answers = {}
    answers_by_code = {}
    validation_errors = {}

    for question in questions:
        field_name = f"question_{question.id}"

        raw_answer = request.POST.get(
            field_name,
            "",
        ).strip()

        # Required question cannot be blank.
        if question.is_required and not raw_answer:
            validation_errors[field_name] = (
                "This question is required."
            )
            continue

        # Optional unanswered question.
        if not raw_answer:
            normalized_answers[question.id] = ""
            answers_by_code[question.question_code] = ""
            continue

        # -----------------------------------------------------
        # BOOLEAN
        # -----------------------------------------------------
        if question.answer_type == "BOOLEAN":
            if raw_answer not in ("true", "false"):
                validation_errors[field_name] = (
                    "Please select Yes or No."
                )
                continue

            normalized_answer = raw_answer

        # -----------------------------------------------------
        # DATE
        # -----------------------------------------------------
        elif question.answer_type == "DATE":
            parsed_date = parse_date(raw_answer)

            if parsed_date is None:
                validation_errors[field_name] = (
                    "Please enter a valid date."
                )
                continue

            normalized_answer = parsed_date.isoformat()

        # -----------------------------------------------------
        # NUMBER
        # -----------------------------------------------------
        elif question.answer_type == "NUMBER":
            try:
                parsed_number = Decimal(raw_answer)

                if not parsed_number.is_finite():
                    raise InvalidOperation

            except (InvalidOperation, ValueError):
                validation_errors[field_name] = (
                    "Please enter a valid number."
                )
                continue

            normalized_answer = str(parsed_number)

        # -----------------------------------------------------
        # TEXT
        # -----------------------------------------------------
        elif question.answer_type == "TEXT":
            normalized_answer = raw_answer

        else:
            validation_errors[field_name] = (
                "Unsupported question type."
            )
            continue

        # screening_answers.answer_value has max length 255.
        if len(normalized_answer) > 255:
            validation_errors[field_name] = (
                "This answer is too long."
            )
            continue

        normalized_answers[question.id] = normalized_answer

        answers_by_code[
            question.question_code
        ] = normalized_answer

    # ---------------------------------------------------------
    # 7. RETURN FORM IF VALIDATION FAILED
    # ---------------------------------------------------------
    if validation_errors:
        # Attach submitted values and validation messages to each
        # question so the template can display them directly.
        for question in questions:
            field_name = f"question_{question.id}"

            question.validation_error = validation_errors.get(
                field_name
            )

            question.submitted_answer = request.POST.get(
                field_name,
                "",
            )
        context = {
            "request_match": request_match,
            "emergency_request": request_match.request,
            "facility": request_match.request.facility,
            "screening": screening,
            "questions": questions,
            "access_token": token,
            "validation_errors": validation_errors,
            "submitted_answers": request.POST,
        }

        return render(
            request,
            "donor/emergency_screening.html",
            context,
            status=400,
        )

    # ---------------------------------------------------------
    # 8. CALCULATE PRELIMINARY RESULT
    # ---------------------------------------------------------
    preliminary_result, flagged_answers = (
        evaluate_emergency_screening(
            answers_by_code
        )
    )

    # ---------------------------------------------------------
    # 9. SAVE EVERYTHING ATOMICALLY
    # ---------------------------------------------------------
    try:
        with transaction.atomic():

            # Lock screening so two submissions cannot complete
            # the same screening at the same time.
            locked_screening = (
                EligibilityScreenings.objects
                .select_for_update()
                .get(id=screening.id)
            )

            if locked_screening.status != "IN_PROGRESS":
                return HttpResponseBadRequest(
                    "This screening has already been submitted."
                )

            now = timezone.now()

            for question in questions:
                question_code = question.question_code

                ScreeningAnswers.objects.create(
                    screening=locked_screening,
                    question=question,
                    answer_value=normalized_answers.get(
                        question.id,
                        "",
                    ),
                    is_flagged=(
                        question_code
                        in flagged_answers
                    ),
                    flag_reason=flagged_answers.get(
                        question_code
                    ),
                    answered_at=now,
                )

            locked_screening.status = "COMPLETED"
            locked_screening.preliminary_result = (
                preliminary_result
            )
            locked_screening.completed_at = now

            locked_screening.save(
                update_fields=[
                    "status",
                    "preliminary_result",
                    "completed_at",
                ]
            )

    except IntegrityError:
        return HttpResponseBadRequest(
            "This screening has already been submitted."
        )

    # ---------------------------------------------------------
    # 10. SHOW RESULT
    # ---------------------------------------------------------
    context = {
        "request_match": request_match,
        "emergency_request": request_match.request,
        "facility": request_match.request.facility,
        "screening": locked_screening,
        "questions": [],
        "screening_completed": True,
        "preliminary_result": preliminary_result,
        "access_token": token,
    }

    return render(
        request,
        "donor/emergency_screening.html",
        context,
    )

def emergency_response_view(request, token):
    """
    Record an ACCEPTED or DECLINED response for a matched donor.

    The secure email token identifies the donor/request match.
    """

    if request.method != "POST":
        return HttpResponseBadRequest(
            "Invalid emergency response request."
        )

    # ---------------------------------------------------------
    # 1. VALIDATE SIGNED EMAIL TOKEN
    # ---------------------------------------------------------
    token_payload = decode_emergency_screening_token(token)

    if token_payload is None:
        return HttpResponseBadRequest(
            "This emergency response link is invalid or has expired."
        )

    match_id = token_payload.get("match_id")
    donor_id = token_payload.get("donor_id")

    # ---------------------------------------------------------
    # 2. VALIDATE DONOR ACTION
    # ---------------------------------------------------------
    response_action = request.POST.get(
        "response_action",
        "",
    ).strip().lower()

    if response_action not in (
        "accept",
        "decline",
    ):
        return HttpResponseBadRequest(
            "Invalid emergency response."
        )

    # ---------------------------------------------------------
    # 3. UPDATE MATCH SAFELY
    # ---------------------------------------------------------
    try:
        with transaction.atomic():

            # Lock the match so a rapid double-click cannot
            # record conflicting ACCEPTED / DECLINED responses.
            request_match = (
                RequestMatches.objects
                .select_for_update()
                .select_related(
                    "request",
                    "request__facility",
                    "donor",
                    "donor__user",
                )
                .get(
                    id=match_id,
                    donor_id=donor_id,
                )
            )

            # Emergency must still be active and within its
            # configured expiration time.
            emergency_request = request_match.request

            if (
                emergency_request.status != "ACTIVE"
                or (
                    emergency_request.expires_at is not None
                    and emergency_request.expires_at <= timezone.now()
                )
            ):
                return HttpResponseBadRequest(
                    "This emergency request is no longer active."
                )

            if request_match.response_status == "EXPIRED":
                return HttpResponseBadRequest(
                    "This emergency donor match has expired."
                )

            # Already answered.
            if request_match.response_status != "PENDING":
                return redirect(
                    "emergency_screening",
                    token=token,
                )

            # -------------------------------------------------
            # 4. REQUIRE COMPLETED PRE-SCREENING
            # -------------------------------------------------
            completed_screening = (
                EligibilityScreenings.objects
                .filter(
                    request_match=request_match,
                    screening_type="EMERGENCY",
                    status="COMPLETED",
                )
                .order_by("-completed_at")
                .first()
            )

            if completed_screening is None:
                return HttpResponseBadRequest(
                    "Please complete the emergency screening first."
                )

            # -------------------------------------------------
            # 5. ACCEPTANCE REQUIRES PRELIMINARY ELIGIBILITY
            # -------------------------------------------------
            if (
                response_action == "accept"
                and completed_screening.preliminary_result
                != "PRELIMINARY_ELIGIBLE"
            ):
                return HttpResponseBadRequest(
                    "This emergency request cannot be accepted "
                    "until the screening requirements are satisfied."
                )

            # -------------------------------------------------
            # 6. RECORD RESPONSE
            # -------------------------------------------------
            if response_action == "accept":
                request_match.response_status = "ACCEPTED"
            else:
                request_match.response_status = "DECLINED"

            request_match.responded_at = timezone.now()

            request_match.save(
                update_fields=[
                    "response_status",
                    "responded_at",
                ]
            )

    except RequestMatches.DoesNotExist:
        return HttpResponseBadRequest(
            "The emergency donor match could not be found."
        )

    return redirect(
        "emergency_screening",
        token=token,
    )