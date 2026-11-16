
import re
import boto3

from django.conf import settings


def get_neon_storage_client():
    """
    Creates an S3-compatible connection to Neon Object Storage.
    """

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def upload_donor_profile_image(uploaded_file, username):
    """
    Uploads or replaces a donor profile image in Neon Object Storage.
    Uses the same object key for each donor, so a new upload replaces
    their previous profile image.
    """

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    if not bucket_name:
        raise ValueError("Neon storage bucket name is not configured.")

    if not uploaded_file.content_type or not uploaded_file.content_type.startswith("image/"):
        raise ValueError("Please upload a valid image.")

    # Keep the username safe for use in an object key.
    safe_username = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        username.strip()
    )

    if not safe_username:
        raise ValueError("Invalid donor username.")

    # Fixed key means uploading again replaces the previous image.
    image_key = f"donor-profiles/{safe_username}/profile-image"

    client = get_neon_storage_client()

    uploaded_file.seek(0)

    client.upload_fileobj(
        uploaded_file,
        bucket_name,
        image_key,
        ExtraArgs={
            "ContentType": uploaded_file.content_type,
        },
    )

    return image_key

def get_donor_profile_image_url(image_key):
    """
    Generate a temporary URL for a donor's profile image.
    """

    if not image_key:
        return None

    client = get_neon_storage_client()

    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": image_key,
        },
        ExpiresIn=3600,
    )
