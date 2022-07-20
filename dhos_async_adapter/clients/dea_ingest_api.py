from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request
from dhos_async_adapter.helpers import security


def post_to_dea_ingest(export_data: Dict) -> None:
    """
    This is not an internal request, it's to the DEA Ingest API so we need different authorization.
    """
    url = f"{config.DEA_INGEST_API_URL}/dea/ingest/v2/dhos_data"
    logger.debug(
        "POSTing data to DEA Ingest API",
        extra={"url": url},
    )
    do_request(
        url=url,
        method="post",
        headers=security.get_dea_request_headers(),
        payload=export_data,
    )
