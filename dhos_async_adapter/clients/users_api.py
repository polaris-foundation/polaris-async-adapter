from typing import Dict, List, Optional

import requests
from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request
from dhos_async_adapter.helpers.exceptions import RejectMessageError


def get_clinician_by_uuid(clinician_uuid: str) -> Optional[Dict]:
    url = f"{config.DHOS_USERS_API_URL}/dhos/v1/clinician/{clinician_uuid}"
    logger.debug(
        "GETting clinician with UUID %s",
        clinician_uuid,
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="get", allow_http_error=True
    )
    if response.status_code == 404:
        return None
    if response.status_code not in range(200, 300):
        logger.exception("Unexpected response from API (HTTP %d)", response.status_code)
        raise RejectMessageError()
    return response.json()


def get_clinicians_by_uuids(
    clinician_uuids: List[str], compact: bool = False
) -> Dict[str, Dict]:
    url = f"{config.DHOS_USERS_API_URL}/dhos/v1/clinician_list"
    params = {"compact": compact}
    logger.debug(
        "POST to clinician_list with UUIDs: %s",
        ", ".join(clinician_uuids),
        extra={"url": url},
    )
    response: requests.Response = do_request(
        url=url, method="post", payload=clinician_uuids, params=params
    )
    return response.json()
