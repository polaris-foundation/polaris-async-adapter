from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def create_reading(reading: Dict) -> None:
    url = f"{config.GDM_BG_READINGS_API_URL}/gdm/v1/process_alerts/reading/{reading['uuid']}"
    logger.debug(
        "POSTing BG reading",
        extra={"url": url},
    )
    do_request(url=url, method="post")
