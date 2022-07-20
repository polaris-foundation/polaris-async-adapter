from typing import Dict

from she_logging import logger

from dhos_async_adapter import config
from dhos_async_adapter.clients import do_request


def aggregate_send_ward_report_data(
    location_uuid: str, start_date: str, end_date: str
) -> Dict:
    url = f"{config.DHOS_AGGREGATOR_API_URL}/dhos/v1/send_ward_report_data"
    logger.debug(
        "Aggregating SEND ward report data for location %s",
        location_uuid,
        extra={"url": url},
    )
    params: Dict = {
        "location_uuid": location_uuid,
        "start_date": start_date,
        "end_date": end_date,
    }
    # TODO SEND-2499 - In App Ward Reporting Phase 1
    # Temporary increase of timeout prior to ward report PDF replacement
    response = do_request(url=url, method="get", params=params, timeout=600)
    return response.json()
