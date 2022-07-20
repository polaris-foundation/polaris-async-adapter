from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def create_clinician(clinician_details: Dict) -> None:
    url = f"{config.DHOS_ACTIVATION_AUTH_API_URL}/dhos/v1/clinician"
    logger.debug(
        "Posting activation auth clinician",
        extra={"url": url, "payload": clinician_details},
    )
    do_request(url=url, method="post", payload=clinician_details)


def update_clinician(clinician_uuid: str, clinician_details: Dict) -> None:
    url = f"{config.DHOS_ACTIVATION_AUTH_API_URL}/dhos/v1/clinician/{clinician_uuid}"
    logger.debug(
        "Patching activation auth clinician",
        extra={"url": url, "payload": clinician_details},
    )
    do_request(url=url, method="patch", payload=clinician_details)
