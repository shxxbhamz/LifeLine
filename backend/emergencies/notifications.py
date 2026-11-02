import logging
import threading
from datetime import timedelta

import requests

from django.conf import settings
from django.db import close_old_connections
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from screening.tokens import create_emergency_screening_token

from .models import Notifications, RequestMatches


logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

MAX_EMAIL_ATTEMPTS = 3

MAX_PERSISTENT_RETRY_COUNT = 5



class EmailNotification:
    """
    Concrete emergency notification implementation.

    LifeLine currently supports EMAIL as its emergency
    notification channel.
    """

    def send(self, request_match):
        if request_match is None:
            return False

        donor = getattr(request_match, "donor", None)
        user = getattr(donor, "user", None)
        emergency_request = getattr(
            request_match,
            "request",
            None,
        )

        if (
            donor is None
            or user is None
            or emergency_request is None
        ):
            return False

        if not user.email:
            return False

        facility = getattr(
            emergency_request,
            "facility",
            None,
        )

        if facility is None:
            return False

        # -------------------------------------------------
        # CREATE SECURE SCREENING LINK
        # -------------------------------------------------
        token = create_emergency_screening_token(
            request_match
        )

        screening_path = reverse(
            "emergency_screening",
            kwargs={
                "token": token,
            },
        )

        # We will add this environment variable on Render
        # later. The production URL is the temporary fallback.
        base_url = getattr(
            settings,
            "LIFELINE_BASE_URL",
            "https://lifeline-85fz.onrender.com",
        ).rstrip("/")

        screening_url = (
            f"{base_url}{screening_path}"
        )

        # -------------------------------------------------
        # EMAIL CONTENT
        # -------------------------------------------------
        donor_name = (
            user.first_name.strip()
            if user.first_name
            else "Donor"
        )

        facility_name = facility.name

        blood_type = (
            emergency_request.required_blood_type
        )

        component = (
            emergency_request.component_type
            .replace("_", " ")
            .title()
        )

        urgency = (
            emergency_request.urgency
            .replace("_", " ")
            .title()
        )

        if request_match.distance_km is not None:
            distance_text = (
                f"{request_match.distance_km} km"
            )
        else:
            distance_text = "Not available"

        subject = (
            f"LifeLine {urgency} Donation Request"
        )

        text_message = f"""Hello {donor_name},

LifeLine has identified you as a potential compatible donor for an emergency donation request.

Emergency Request:
Facility: {facility_name}
Blood Type Required: {blood_type}
Component: {component}
Urgency: {urgency}
Approximate Distance: {distance_text}

Please complete the secure emergency pre-screening using the link below:

{screening_url}

The screening provides a preliminary result only. Final donation eligibility may require review by qualified healthcare staff.

This secure link was generated specifically for your donor match. Please do not share it.

Thank you for responding quickly.

LifeLine Emergency Team
"""

        safe_donor_name = escape(donor_name)
        safe_facility_name = escape(
            facility_name
        )
        safe_blood_type = escape(blood_type)
        safe_component = escape(component)
        safe_urgency = escape(urgency)
        safe_distance = escape(distance_text)
        safe_screening_url = escape(
            screening_url
        )

        html_message = f"""
<!DOCTYPE html>
<html>
<body style="
    margin:0;
    padding:0;
    background:#f4f7f7;
    font-family:Arial,Helvetica,sans-serif;
    color:#263238;
">

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="padding:30px 15px;"
>
<tr>
<td align="center">

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        max-width:620px;
        background:#ffffff;
        border-radius:12px;
        overflow:hidden;
        box-shadow:0 4px 18px rgba(0,0,0,0.08);
    "
>

<tr>
<td style="
    background:#3AAFA9;
    padding:24px;
    text-align:center;
    color:#ffffff;
">
    <div style="
        font-size:26px;
        font-weight:700;
    ">
        LifeLine
    </div>

    <div style="
        margin-top:5px;
        font-size:14px;
    ">
        Emergency Donor Response
    </div>
</td>
</tr>


<tr>
<td style="padding:30px;">

    <h2 style="
        margin-top:0;
        color:#D9534F;
    ">
        {safe_urgency} Donation Request
    </h2>

    <p>
        Hello <strong>{safe_donor_name}</strong>,
    </p>

    <p style="line-height:1.6;">
        You have been identified as a potential
        compatible donor for an emergency donation
        request.
    </p>


    <table
        width="100%"
        cellpadding="10"
        cellspacing="0"
        style="
            margin:22px 0;
            background:#f8fbfb;
            border-radius:8px;
        "
    >

        <tr>
            <td>
                <strong>Facility</strong>
            </td>

            <td align="right">
                {safe_facility_name}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Blood Type</strong>
            </td>

            <td align="right">
                {safe_blood_type}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Component</strong>
            </td>

            <td align="right">
                {safe_component}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Urgency</strong>
            </td>

            <td
                align="right"
                style="
                    color:#D9534F;
                    font-weight:700;
                "
            >
                {safe_urgency}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Distance</strong>
            </td>

            <td align="right">
                {safe_distance}
            </td>
        </tr>

    </table>


    <p style="
        line-height:1.6;
        text-align:center;
    ">
        Please complete the short secure
        pre-screening before responding.
    </p>


    <div style="
        text-align:center;
        margin:28px 0;
    ">

        <a
            href="{safe_screening_url}"
            style="
                display:inline-block;
                padding:14px 24px;
                background:#D9534F;
                color:#ffffff;
                text-decoration:none;
                border-radius:7px;
                font-weight:700;
            "
        >
            Complete Emergency Screening
        </a>

    </div>


    <div style="
        margin-top:24px;
        padding:14px;
        background:#eef8f7;
        border-radius:7px;
        font-size:13px;
        line-height:1.6;
        color:#526466;
    ">
        LifeLine provides a preliminary screening
        result only. Final donation eligibility may
        require review by qualified healthcare staff.
    </div>


    <p style="
        margin-top:24px;
        color:#7a8589;
        font-size:12px;
        line-height:1.5;
        text-align:center;
    ">
        This secure link was generated specifically
        for your emergency donor match.
        Please do not share it.
    </p>

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""

        # -------------------------------------------------
        # CREATE PERSISTENT NOTIFICATION RECORD FIRST
        # -------------------------------------------------
        now = timezone.now()

        notification = Notifications.objects.create(
            user=user,
            emergency_request=emergency_request,
            request_match=request_match,
            notification_type="EMERGENCY_ALERT",
            title=subject,
            message=text_message,
            delivery_channel="EMAIL",
            delivery_status="PENDING",
            retry_count=0,
            is_read=False,
            created_at=now,
            sent_at=None,
            read_at=None,
        )

        # -------------------------------------------------
        # SEND IN BACKGROUND
        # -------------------------------------------------
        email_thread = threading.Thread(
            target=_deliver_emergency_email,
            args=(
                notification.id,
                request_match.id,
                user.email,
                donor_name,
                subject,
                text_message,
                html_message,
            ),
            daemon=True,
        )

        email_thread.start()

        return True


class NotificationFactory:
    """
    Simple Factory responsible for creating the
    appropriate notification implementation.
    """

    @staticmethod
    def create_notification(channel):
        channel = (
            channel or ""
        ).strip().upper()

        if channel == "EMAIL":
            return EmailNotification()

        raise ValueError(
            f"Unsupported notification channel: {channel}"
        )


def _deliver_emergency_email(
    notification_id,
    request_match_id,
    user_email,
    donor_name,
    subject,
    text_message,
    html_message,
):
    """
    Background worker that sends an emergency email
    and updates persistent delivery state.

    Up to three delivery attempts are made.
    """

    close_old_connections()

    api_key = getattr(
        settings,
        "BREVO_API_KEY",
        None,
    )

    sender_email = getattr(
        settings,
        "BREVO_SENDER_EMAIL",
        None,
    )

    sender_name = getattr(
        settings,
        "BREVO_SENDER_NAME",
        "LifeLine Emergency Team",
    )

    if not api_key or not sender_email:
        Notifications.objects.filter(
            id=notification_id
        ).update(
            delivery_status="FAILED",
        )

        RequestMatches.objects.filter(
            id=request_match_id
        ).update(
            notification_status="FAILED",
        )

        close_old_connections()
        return

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [
            {
                "email": user_email,
                "name": donor_name,
            }
        ],
        "subject": subject,
        "textContent": text_message,
        "htmlContent": html_message,
    }

    for attempt_number in range(
        1,
        MAX_EMAIL_ATTEMPTS + 1,
    ):
        try:
            response = requests.post(
                BREVO_API_URL,
                headers={
                    "accept": "application/json",
                    "api-key": api_key,
                    "content-type": "application/json",
                },
                json=payload,
                timeout=20,
            )

            response.raise_for_status()

        except requests.RequestException:
            logger.exception(
                "Emergency email attempt %s failed "
                "for RequestMatch %s.",
                attempt_number,
                request_match_id,
            )

            # retry_count counts retries after the
            # initial delivery attempt.
            retry_count = max(
                0,
                attempt_number - 1,
            )

            Notifications.objects.filter(
                id=notification_id
            ).update(
                retry_count=retry_count,
            )

            if attempt_number == MAX_EMAIL_ATTEMPTS:
                Notifications.objects.filter(
                    id=notification_id
                ).update(
                    delivery_status="FAILED",
                    retry_count=(
                        MAX_EMAIL_ATTEMPTS - 1
                    ),
                )

                RequestMatches.objects.filter(
                    id=request_match_id
                ).update(
                    notification_status="FAILED",
                )

            continue

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------
        sent_at = timezone.now()

        Notifications.objects.filter(
            id=notification_id
        ).update(
            delivery_status="SENT",
            sent_at=sent_at,
            retry_count=max(
                0,
                attempt_number - 1,
            ),
        )

        RequestMatches.objects.filter(
            id=request_match_id
        ).update(
            notification_status="SENT",
            notified_at=sent_at,
        )

        break

    close_old_connections()

def dispatch_emergency_notification_wave(
    request_matches,
):
    """
    Dispatch emergency emails to the selected donor wave.

    A donor match is skipped when:
        - it has already been contacted,
        - it has already responded, or
        - an emergency notification record already exists.

    Returns summary counts for logging/testing.
    """

    results = {
        "selected": 0,
        "dispatched": 0,
        "skipped": 0,
        "failed": 0,
    }

    if not request_matches:
        return results

    notification_sender = (
        NotificationFactory.create_notification(
            "EMAIL"
        )
    )

    for request_match in request_matches:
        results["selected"] += 1

        # -------------------------------------------------
        # ONLY UNCONTACTED / UNANSWERED MATCHES
        # -------------------------------------------------
        if (
            request_match.notification_status
            != "PENDING"
            or request_match.response_status
            != "PENDING"
        ):
            results["skipped"] += 1
            continue

        # -------------------------------------------------
        # DUPLICATE PROTECTION
        #
        # If dispatch is accidentally triggered again before
        # the donor responds, do not create/send another
        # emergency alert for the same RequestMatch.
        # -------------------------------------------------
        existing_notification = (
            Notifications.objects
            .filter(
                request_match=request_match,
                notification_type="EMERGENCY_ALERT",
            )
            .exists()
        )

        if existing_notification:
            results["skipped"] += 1
            continue

        # -------------------------------------------------
        # SEND THROUGH SIMPLE FACTORY PRODUCT
        # -------------------------------------------------
        try:
            was_dispatched = (
                notification_sender.send(
                    request_match
                )
            )

        except Exception:
            logger.exception(
                "Emergency notification dispatch failed "
                "for RequestMatch %s.",
                request_match.id,
            )

            results["failed"] += 1
            continue

        if was_dispatched:
            results["dispatched"] += 1
        else:
            results["failed"] += 1

    return results

def retry_failed_emergency_notifications(
    limit=25,
):
    """
    Retry emergency emails that previously failed.

    This function uses the EXISTING Notifications row.
    It does not create a duplicate notification.

    Only notifications are retried when:
        - delivery previously FAILED
        - notification is an emergency alert
        - delivery channel is EMAIL
        - retry limit has not been reached
        - emergency is still ACTIVE
        - donor has not already responded

    One persistent retry is attempted per call so a
    scheduler can space retries over time.
    """

    results = {
        "found": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
    }

    stale_pending_cutoff = (
        timezone.now() - timedelta(minutes=2)
    )

    failed_notifications = (
        Notifications.objects
        .select_related(
            "user",
            "emergency_request",
            "emergency_request__facility",
            "request_match",
            "request_match__donor",
            "request_match__donor__user",
        )
        .filter(
            notification_type="EMERGENCY_ALERT",
            delivery_channel="EMAIL",
            retry_count__lt=MAX_PERSISTENT_RETRY_COUNT,
            request_match__isnull=False,
            emergency_request__isnull=False,
        )
        .filter(
            Q(delivery_status="FAILED")
            | Q(
                delivery_status="PENDING",
                created_at__lte=stale_pending_cutoff,
            )
        )
        .order_by(
            "created_at",
            "id",
        )[:limit]
    )

    api_key = getattr(
        settings,
        "BREVO_API_KEY",
        None,
    )

    sender_email = getattr(
        settings,
        "BREVO_SENDER_EMAIL",
        None,
    )

    sender_name = getattr(
        settings,
        "BREVO_SENDER_NAME",
        "LifeLine Emergency Team",
    )

    for notification in failed_notifications:
        results["found"] += 1

        request_match = notification.request_match
        emergency_request = (
            notification.emergency_request
        )

        # -------------------------------------------------
        # DO NOT RETRY OBSOLETE EMERGENCIES
        # -------------------------------------------------
        if (
            emergency_request.status != "ACTIVE"
            or request_match.response_status != "PENDING"
        ):
            results["skipped"] += 1
            continue

        user = notification.user

        if (
            user is None
            or not user.email
            or not api_key
            or not sender_email
        ):
            notification.retry_count += 1

            notification.save(
                update_fields=[
                    "retry_count",
                ]
            )

            results["failed"] += 1
            continue

        # -------------------------------------------------
        # GENERATE A FRESH SECURE LINK
        #
        # We do not reuse the old signed URL because the
        # token may have become too old by retry time.
        # -------------------------------------------------
        token = create_emergency_screening_token(
            request_match
        )

        screening_path = reverse(
            "emergency_screening",
            kwargs={
                "token": token,
            },
        )

        base_url = getattr(
            settings,
            "LIFELINE_BASE_URL",
            "https://lifeline-85fz.onrender.com",
        ).rstrip("/")

        screening_url = (
            f"{base_url}{screening_path}"
        )

        facility = emergency_request.facility

        donor_name = (
            user.first_name.strip()
            if user.first_name
            else "Donor"
        )

        facility_name = (
            facility.name
            if facility
            else "LifeLine Facility"
        )

        blood_type = (
            emergency_request.required_blood_type
        )

        component = (
            emergency_request.component_type
            .replace("_", " ")
            .title()
        )

        urgency = (
            emergency_request.urgency
            .replace("_", " ")
            .title()
        )

        distance_text = (
            f"{request_match.distance_km} km"
            if request_match.distance_km
            is not None
            else "Not available"
        )

        # -------------------------------------------------
        # REBUILD MESSAGE WITH FRESH TOKEN
        # -------------------------------------------------
        text_message = f"""Hello {donor_name},

LifeLine is retrying an emergency donation notification that could not be delivered earlier.

Emergency Request:
Facility: {facility_name}
Blood Type Required: {blood_type}
Component: {component}
Urgency: {urgency}
Approximate Distance: {distance_text}

Please complete the secure emergency pre-screening:

{screening_url}

This screening provides a preliminary result only. Final donation eligibility may require review by qualified healthcare staff.

Please do not share this secure link.

LifeLine Emergency Team
"""

        safe_donor_name = escape(
            donor_name
        )

        safe_facility_name = escape(
            facility_name
        )

        safe_blood_type = escape(
            blood_type
        )

        safe_component = escape(
            component
        )

        safe_urgency = escape(
            urgency
        )

        safe_screening_url = escape(
            screening_url
        )

        html_message = f"""
<!DOCTYPE html>
<html>
<body style="
    margin:0;
    padding:30px 15px;
    background:#f4f7f7;
    font-family:Arial,Helvetica,sans-serif;
    color:#263238;
">

<div style="
    max-width:600px;
    margin:0 auto;
    background:#ffffff;
    border-radius:12px;
    overflow:hidden;
">

    <div style="
        background:#3AAFA9;
        color:#ffffff;
        padding:24px;
        text-align:center;
        font-size:25px;
        font-weight:700;
    ">
        LifeLine Emergency Response
    </div>

    <div style="padding:30px;">

        <h2 style="color:#D9534F;">
            {safe_urgency} Donation Request
        </h2>

        <p>
            Hello
            <strong>{safe_donor_name}</strong>,
        </p>

        <p>
            We are retrying an emergency alert that
            could not be delivered earlier.
        </p>

        <div style="
            margin:20px 0;
            padding:18px;
            background:#f7fafa;
            border-radius:8px;
            line-height:1.8;
        ">
            <strong>Facility:</strong>
            {safe_facility_name}
            <br>

            <strong>Blood Type:</strong>
            {safe_blood_type}
            <br>

            <strong>Component:</strong>
            {safe_component}
            <br>

            <strong>Urgency:</strong>
            {safe_urgency}
        </div>

        <div style="
            text-align:center;
            margin:28px 0;
        ">

            <a
                href="{safe_screening_url}"
                style="
                    display:inline-block;
                    padding:14px 24px;
                    background:#D9534F;
                    color:#ffffff;
                    text-decoration:none;
                    border-radius:7px;
                    font-weight:700;
                "
            >
                Complete Emergency Screening
            </a>

        </div>

        <p style="
            color:#68777a;
            font-size:13px;
            line-height:1.6;
        ">
            This is a secure donor-specific link.
            Please do not share it.
        </p>

    </div>

</div>

</body>
</html>
"""

        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {
                    "email": user.email,
                    "name": donor_name,
                }
            ],
            "subject": notification.title,
            "textContent": text_message,
            "htmlContent": html_message,
        }

        # -------------------------------------------------
        # ONE PERSISTENT RETRY ATTEMPT
        # -------------------------------------------------
        try:
            response = requests.post(
                BREVO_API_URL,
                headers={
                    "accept": "application/json",
                    "api-key": api_key,
                    "content-type": "application/json",
                },
                json=payload,
                timeout=20,
            )

            response.raise_for_status()

        except requests.RequestException:
            logger.exception(
                "Persistent emergency email retry "
                "failed for notification %s.",
                notification.id,
            )

            notification.retry_count += 1
            notification.delivery_status = "FAILED"

            notification.save(
                update_fields=[
                    "retry_count",
                    "delivery_status",
                ]
            )

            request_match.notification_status = (
                "FAILED"
            )

            request_match.save(
                update_fields=[
                    "notification_status",
                ]
            )

            results["failed"] += 1
            continue

        # -------------------------------------------------
        # RETRY SUCCEEDED
        # -------------------------------------------------
        sent_at = timezone.now()

        notification.delivery_status = "SENT"
        notification.sent_at = sent_at

        notification.save(
            update_fields=[
                "delivery_status",
                "sent_at",
            ]
        )

        request_match.notification_status = "SENT"
        request_match.notified_at = sent_at

        request_match.save(
            update_fields=[
                "notification_status",
                "notified_at",
            ]
        )

        results["sent"] += 1

    return results