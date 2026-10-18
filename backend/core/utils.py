import threading
import resend
from django.conf import settings

# Initialize Resend with your API key from environment variables
resend.api_key = getattr(settings, 'RESEND_API_KEY', None)

def _send_email_async(subject, message, recipient_email):
    """Sends email via Resend's HTTPS API in a background thread."""
    try:
        params = {
            "from": "LifeLine Emergency Team <onboarding@resend.dev>",
            "to": [recipient_email],
            "subject": subject,
            "text": message,
        }
        resend.emails.send(params)
    except Exception as e:
        print(f"Resend email dispatch error: {e}")

def send_welcome_email(user_email, username, role):
    """
    Sends an automated welcome email via Resend asynchronously.
    """
    subject = f"Welcome to LifeLine, {username}!"
    
    role_lower = role.lower() if role else 'donor'
    if 'donor' in role_lower:
        role_message = "Thank you for registering as a Blood Donor! Your contributions can save lives."
    elif 'hospital' in role_lower:
        role_message = "Welcome! As Hospital Staff, you can now request blood units and manage urgent patient needs."
    elif 'blood_bank' in role_lower or 'blood bank' in role_lower:
        role_message = "Welcome! As Blood Bank Staff, you can now manage blood inventory and coordinate requests."
    else:
        role_message = "Thank you for joining our healthcare platform!"

    message = f"""Hello {username},

{role_message}

We are excited to have you on board with LifeLine. 

Best regards,
The LifeLine Team"""

    # Dispatch via background thread so registration remains instant
    email_thread = threading.Thread(
        target=_send_email_async,
        args=(subject, message, user_email)
    )
    email_thread.start()