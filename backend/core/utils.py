import threading
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_email_async(payload, api_key):
    """Helper function to send the email via Brevo HTTPS API in a background thread."""
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
        logger.info("Brevo successfully accepted the email request.")
    except requests.RequestException as e:
        logger.exception("Brevo failed to send the email in background thread: %s",e,)


def send_welcome_email(user_email, username, role):
    """Send a LifeLine welcome email asynchronously using the Brevo HTTPS API."""

    if not user_email:
        logger.error("Welcome email skipped: recipient email is empty.")
        return False

    api_key = getattr(settings, "BREVO_API_KEY", None)
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", None)
    sender_name = getattr(
        settings, "BREVO_SENDER_NAME", "LifeLine Emergency Team"
    )

    if not api_key or not sender_email:
        logger.error("Brevo email configuration is missing or invalid.")
        return False

    subject = f"Welcome to LifeLine, {username}!"

    role_lower = (role or "donor").lower().replace("_", " ").strip()

    if "donor" in role_lower:
        role_message = (
            "Thank you for registering as a Blood Donor! "
            "Your contributions can save lives."
        )
    elif "hospital" in role_lower:
        role_message = (
            "Welcome to LifeLine! You can now request blood units "
            "and manage urgent patient needs."
        )
    elif "blood bank" in role_lower:
        role_message = (
            "Welcome to LifeLine! You can now manage blood inventory "
            "and coordinate blood requests."
        )
    else:
        role_message = (
            "Thank you for joining our healthcare platform. "
            "We are happy to have you as part of LifeLine."
        )

    message = f"""Hello {username},

Your LifeLine account has been created successfully!

{role_message}

We are excited to have you on board with LifeLine.

If you need assistance, please contact our team.

Best regards,
LifeLine Emergency Team
"""

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [{"email": user_email}],
        "subject": subject,
        "textContent": message,
    }

    # Dispatch via background thread so user registration isn't laggy
    email_thread = threading.Thread(
        target=_send_email_async,
        args=(payload, api_key),
    )
    email_thread.start()
    return True



def send_appointment_status_email(
    user_email,
    first_name,
    facility_name,
    scheduled_at,
    donation_type,
    status,
):
    """
    Send an appointment confirmation or cancellation email
    asynchronously using the existing Brevo API configuration.
    """

    if not user_email:
        logger.error("Appointment email skipped: recipient email is empty.")
        return False

    api_key = getattr(settings, "BREVO_API_KEY", None)
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", None)
    sender_name = getattr(
        settings,
        "BREVO_SENDER_NAME",
        "LifeLine Emergency Team",
    )

    if not api_key or not sender_email:
        logger.error("Brevo email configuration is missing or invalid.")
        return False

    donor_name = first_name or "Donor"
    facility_name = facility_name or "your selected LifeLine facility"

    if scheduled_at:
        appointment_time = scheduled_at.strftime(
            "%B %d, %Y at %I:%M %p"
        )
    else:
        appointment_time = "your scheduled time"

    donation_label = (
        donation_type.replace("_", " ").title()
        if donation_type
        else "Donation"
    )

    status = (status or "").upper()

    if status == "CONFIRMED":
        subject = "Your LifeLine Appointment Has Been Confirmed"

        message = f"""Hello {donor_name},

Your donation appointment has been confirmed by {facility_name}.

Appointment Details:
Facility: {facility_name}
Donation Type: {donation_label}
Scheduled Time: {appointment_time}
Status: Confirmed

Please arrive on time and follow any preparation instructions provided by the facility.

Thank you for supporting LifeLine and helping save lives.

Best regards,
LifeLine Team
"""

    elif status == "CANCELLED":
        subject = "Your LifeLine Appointment Has Been Cancelled"

        message = f"""Hello {donor_name},

Your donation appointment at {facility_name} has been cancelled.

Appointment Details:
Facility: {facility_name}
Donation Type: {donation_label}
Scheduled Time: {appointment_time}
Status: Cancelled

You may book another appointment when scheduling becomes available.

Thank you for supporting LifeLine.

Best regards,
LifeLine Team
"""

    else:
        logger.error(
            "Appointment email skipped: unsupported status %s.",
            status,
        )
        return False

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
        "textContent": message,
    }

    email_thread = threading.Thread(
        target=_send_email_async,
        args=(payload, api_key),
    )
    email_thread.start()

    return True

#Heer Patel #
def send_donor_booking_email(
    user_email,
    first_name,
    facility_name,
    scheduled_at,
    donation_type,
):
    """Send an email when a donor submits an appointment request."""

    if not user_email:
        logger.error("Booking email skipped: recipient email is empty.")
        return False

    api_key = getattr(settings, "BREVO_API_KEY", None)
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", None)
    sender_name = getattr(
        settings,
        "BREVO_SENDER_NAME",
        "LifeLine Emergency Team",
    )

    if not api_key or not sender_email:
        logger.error("Brevo email configuration is missing.")
        return False

    donor_name = first_name or "Donor"

    appointment_time = scheduled_at.strftime(
        "%B %d, %Y at %I:%M %p"
    )

    donation_label = donation_type.replace(
        "_", " "
    ).title()

    subject = "LifeLine - Appointment Request Received"

    message = f"""Hello {donor_name},

Thank you for booking an appointment at {facility_name}.

Your appointment request has been successfully submitted.

Appointment Details:
Facility: {facility_name}
Donation Component: {donation_label}
Scheduled Time: {appointment_time}
Status: Waiting for hospital staff confirmation.

Please allow up to 1 business day for hospital staff to review and confirm your appointment.

You will receive another email once your appointment has been confirmed.

Thank you for supporting LifeLine and helping save lives.

Best regards,
LifeLine Emergency Team
"""

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
        "textContent": message,
    }

    email_thread = threading.Thread(
        target=_send_email_async,
        args=(payload, api_key),
    )

    email_thread.start()

    return True
#Heer Patel#    