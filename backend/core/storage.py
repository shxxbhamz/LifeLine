import logging
import re

import boto3
from botocore.config import Config
from django.conf import settings


logger = logging.getLogger(__name__)


def get_neon_storage_client():
    """
    Create and return an S3-compatible client for Neon Object Storage.
    """

    required_settings = {
        "AWS_S3_ENDPOINT_URL": settings.AWS_S3_ENDPOINT_URL,
        "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
        "AWS_S3_REGION_NAME": settings.AWS_S3_REGION_NAME,
        "AWS_STORAGE_BUCKET_NAME": settings.AWS_STORAGE_BUCKET_NAME,
    }

    missing_settings = [
        name
        for name, value in required_settings.items()
        if not value
    ]

    if missing_settings:
        raise ValueError(
            "Missing Neon storage settings: "
            + ", ".join(missing_settings)
        )

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path",
            },
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def upload_donor_profile_image(uploaded_file, username):
    """
    Upload a donor profile picture to Neon Object Storage.

    Returns the object key to save in donor_profiles.profile_image_key.
    """

    if not uploaded_file:
        raise ValueError("No profile picture was provided.")

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if uploaded_file.content_type not in allowed_types:
        raise ValueError(
            "Unsupported image format. "
            "Please upload a JPG, PNG, or WEBP image."
        )

    max_file_size = 5 * 1024 * 1024

    if uploaded_file.size > max_file_size:
        raise ValueError(
            "Image must be smaller than 5 MB."
        )

    safe_username = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        username.strip(),
    )

    if not safe_username:
        raise ValueError("Invalid donor username.")

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    # Each donor has one profile picture.
    # Uploading a replacement overwrites the existing object.
    image_key = (
        f"donor-profiles/{safe_username}/profile-image"
    )

    client = get_neon_storage_client()

    uploaded_file.seek(0)

    client.put_object(
        Bucket=bucket_name,
        Key=image_key,
        Body=uploaded_file.read(),
        ContentType=uploaded_file.content_type,
    )

    logger.info(
        "Donor profile picture uploaded successfully. Key: %s",
        image_key,
    )

    return image_key


def get_donor_profile_image_url(image_key):
    """
    Generate a temporary secure URL for a private donor profile picture.
    The URL expires after one hour.
    """

    if not image_key:
        return None

    client = get_neon_storage_client()

    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": image_key,
        },
        ExpiresIn=3600,
    )


def get_safe_donor_avatar_url(donor_profile):
    """
    Safely generate a donor avatar URL.
    Returns None if the profile image is unavailable.
    """

    if not donor_profile or not getattr(
        donor_profile,
        "profile_image_key",
        None,
    ):
        return None

    try:
        return get_donor_profile_image_url(
            donor_profile.profile_image_key
        )

    except Exception:
        logger.exception(
            "Failed to generate presigned URL for key: %s",
            donor_profile.profile_image_key,
        )
        return None


def test_donor_profile_image(image_key):
    """
    Check whether a donor profile image actually exists in Neon.
    Does not expose storage credentials.
    """

    if not image_key:
        return {
            "exists": False,
            "reason": "Image key is empty",
        }

    try:
        client = get_neon_storage_client()

        response = client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=image_key,
        )

        return {
            "exists": True,
            "content_type": response.get("ContentType"),
            "content_length": response.get("ContentLength"),
        }

    except Exception:
        logger.exception(
            "NEON IMAGE OBJECT CHECK FAILED: key=%s",
            image_key,
        )

        return {
            "exists": False,
            "reason": "Storage object check failed",
        }