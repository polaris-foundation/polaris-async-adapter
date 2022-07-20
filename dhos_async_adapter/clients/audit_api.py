from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def create_audit_event(audit_event: Dict) -> None:
    url = f"{config.DHOS_AUDIT_API_URL}/dhos/v2/event"
    logger.debug(
        "POSTing audit message",
        extra={"url": url, "payload": audit_event},
    )
    do_request(url=url, method="post", payload=audit_event)
