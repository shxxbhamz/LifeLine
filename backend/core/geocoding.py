import logging
import os

import requests

logger = logging.getLogger(__name__)

GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/search"


def geocode_address(street_address, city, province, postal_code, country):
    """
    Convert a postal address into latitude and longitude.

    Return (latitude, longitude) if successful.
    Return None if the address cannot be geocoded.
    """

    api_key = os.getenv("GEOAPIFY_API_KEY")

    if not api_key:
        logger.warning("Geoapify API key is not configured.")
        return None

    address = ", ".join(
        str(part).strip()
        for part in (
            street_address,
            city,
            province,
            postal_code,
            country,
        )
        if part
    )

    try:
        response = requests.get(
            GEOAPIFY_URL,
            params={
                "text": address,
                "apiKey": api_key,
                "limit": 1,
            },
            timeout=10,
        )

        response.raise_for_status()

        features = response.json().get("features", [])

        if not features:
            return None

        properties = features[0]["properties"]

        return (
            properties["lat"],
            properties["lon"],
        )

    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.exception("Address geocoding failed.")
        return None