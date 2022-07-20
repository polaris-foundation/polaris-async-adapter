from typing import Dict

import requests
from environs import Env
from requests import Response


def _get_base_url() -> str:
    return Env().str("DHOS_LOCATIONS_BASE_URL", "http://dhos-locations-api:5000")


def post_location(location_data: Dict, jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v1/location",
        headers={"Authorization": f"Bearer {jwt}"},
        json=location_data,
        timeout=15,
    )


def drop_all_data(jwt: str) -> Response:
    response = requests.post(
        f"{_get_base_url()}/drop_data",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response
