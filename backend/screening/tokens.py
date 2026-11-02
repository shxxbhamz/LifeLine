from django.core import signing


EMERGENCY_SCREENING_TOKEN_SALT = (
    "lifeline.emergency-screening"
)

# Emergency email links remain valid for 12 hours.
EMERGENCY_SCREENING_TOKEN_MAX_AGE = 60 * 60 * 12


def create_emergency_screening_token(request_match):
    """
    Create a signed token identifying one specific
    donor/request match.

    The token can safely be placed in an emergency email URL.
    """

    payload = {
        "match_id": request_match.id,
        "donor_id": request_match.donor_id,
    }

    return signing.dumps(
        payload,
        salt=EMERGENCY_SCREENING_TOKEN_SALT,
        compress=True,
    )


def decode_emergency_screening_token(token):
    """
    Validate and decode an emergency screening token.

    Returns the signed payload when valid.
    Returns None if the token is invalid, modified, or expired.
    """

    try:
        payload = signing.loads(
            token,
            salt=EMERGENCY_SCREENING_TOKEN_SALT,
            max_age=EMERGENCY_SCREENING_TOKEN_MAX_AGE,
        )

    except (
        signing.BadSignature,
        signing.SignatureExpired,
    ):
        return None

    if not isinstance(payload, dict):
        return None

    match_id = payload.get("match_id")
    donor_id = payload.get("donor_id")

    if not match_id or not donor_id:
        return None

    return payload