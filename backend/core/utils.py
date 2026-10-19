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
        logger.info("Brevo successfully accepted the welcome email request.")
    except requests.RequestException as e:
        logger.exception("Brevo failed to send the welcome email in background thread: %s", e)


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
