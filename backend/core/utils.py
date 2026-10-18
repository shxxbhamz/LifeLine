import threading
from django.core.mail import send_mail
from django.conf import settings

def _send_email_async(subject, message, recipient_list):
    """Helper function to execute email transmission in a background thread."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Background email dispatch error: {e}")

def send_welcome_email(user_email, username, role):
    """
    Sends an automated welcome email from emergency.lifelineservices999@gmail.com 
    customized by user role, dispatched asynchronously via a background thread.
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
The LifeLine Team
"""

    
    email_thread = threading.Thread(
        target=_send_email_async,
        args=(subject, message, [user_email])
    )
    email_thread.start()