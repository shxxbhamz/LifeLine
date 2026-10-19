
import logging

from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


def send_welcome_email(user_email, username, role):
    """
    Send a welcome email to a newly registered LifeLine user
    using the Gmail SMTP configuration in settings.py.
    """

    # Check that a recipient email address exists.
    if not user_email:
        logger.error(
            "Welcome email skipped because the recipient email is empty."
        )
        return False

    # Prepare the email subject.
    subject = f"Welcome to LifeLine, {username}!"

    # Normalize the user's role.
    role_lower = (role or "donor").lower().replace("_", " ").strip()

    # Customize the message according to the user's role.
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

    # Construct the plain-text email.
    message = f"""Hello {username},

Your LifeLine account has been created successfully!

{role_message}

We are excited to have you on board with LifeLine.

If you need assistance, please contact our team.

Best regards,
LifeLine Emergency Team
"""

    try:
        # Send the email using Django's configured email backend.
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )

        if sent_count == 1:
            logger.info(
                "LifeLine welcome email successfully submitted to %s",
                user_email,
            )
            return True

        logger.error(
            "LifeLine welcome email was not sent to %s",
            user_email,
        )
        return False

    except Exception:
        # Record the full exception in the server logs.
        logger.exception(
            "Error sending LifeLine welcome email to %s",
            user_email,
        )
        return False
