from typing import Any, Dict, List, Optional

import requests
from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def get_locations(
    location_types: Optional[List[str]] = None, compact: bool = True
) -> Dict[str, Dict[str, Any]]:
    url = f"{config.DHOS_LOCATIONS_API_URL}/dhos/v1/location/search"
    logger.debug(
        "GETting locations",
        extra={"url": url},
    )
    params = {
        "location_types": "|".join(location_types) if location_types else None,
        "compact": compact,
    }
    response: requests.Response = do_request(url=url, method="get", params=params)
    result: Dict[str, Dict[str, Any]] = response.json()
    if not isinstance(result, dict):
        raise TypeError("Unexpected response from locations API")
    return result


def get_location_by_uuid(location_uuid: str) -> Dict:
    url = f"{config.DHOS_LOCATIONS_API_URL}/dhos/v1/location/{location_uuid}"
    logger.debug(
        "GETting location with UUID %s",
        location_uuid,
        extra={"url": url},
    )
    response: requests.Response = do_request(url=url, method="get")
    return response.json()


def get_locations_by_ods_code(ods_code: str) -> Dict[str, Dict[str, Any]]:
    params = {
        "ods_code": ods_code,
    }
    url = f"{config.DHOS_LOCATIONS_API_URL}/dhos/v1/location/search"
    logger.debug(
        "GETting locations with ODS code %s",
        ods_code,
        extra={"url": url},
    )
    response: requests.Response = do_request(url=url, method="get", params=params)
    locations: Dict[str, Dict[str, Any]] = response.json()
    if not isinstance(locations, dict):
        raise TypeError("Unexpected response from locations API")
    logger.debug(
        "Retrieved %d locations matching ODS code %s", len(locations), ods_code
    )
    return locations


def create_location(locations_details: Dict) -> Dict:
    url = f"{config.DHOS_LOCATIONS_API_URL}/dhos/v1/location"
    logger.debug(
        "POSTing new location",
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="post", payload=locations_details
    )
    return response.json()
