from typing import AnyStr, Dict, List

from marshmallow import INCLUDE
from she_logging import logger

from dhos_async_adapter.clients import dea_ingest_api
from dhos_async_adapter.helpers import dea_ingest
from dhos_async_adapter.helpers.dea_ingest import ExportMessage
from dhos_async_adapter.helpers.validation import validate_message_body_list

ROUTING_KEY = "dhos.DM000015"


def process(body: AnyStr) -> None:
    """
    - Summary: Exports GDM SYNE blood glucose readings to DEA Ingest API.
    - Routing Key: dhos.DM000015
    - Body: GDM SYNE blood glucose readings reports.
    - Notes: Reports are sent to the central DEA Ingest API.
    - Endpoint(s): POST /dea/ingest/v2/dhos_data (external)
    """
    logger.info(
        "Received 'export GDM SYNE blood glucose readings' message (%s)",
        ROUTING_KEY,
    )

    # Load and validate message body.
    logger.debug(
        "Export GDM SYNE blood glucose readings message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    export_data: List[Dict] = validate_message_body_list(
        body=body, schema=ExportMessage, unknown=INCLUDE
    )

    export_payload: Dict = dea_ingest.generate_dea_ingest_payload(
        export_data=export_data, data_type="syne_bg_readings"
    )

    # Post message to DEA Ingest API.
    dea_ingest_api.post_to_dea_ingest(export_data=export_payload)
