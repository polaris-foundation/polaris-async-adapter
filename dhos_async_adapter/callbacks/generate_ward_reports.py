from typing import AnyStr, Dict, Set

import draymed
from marshmallow import Schema, ValidationError, fields
from she_logging import logger

from dhos_async_adapter.clients import (
    aggregator_api,
    dea_ingest_api,
    locations_api,
    pdf_api,
)
from dhos_async_adapter.helpers import dea_ingest
from dhos_async_adapter.helpers.dea_ingest import ExportMessage
from dhos_async_adapter.helpers.exceptions import (
    RejectMessageError,
    RequeueMessageError,
)
from dhos_async_adapter.helpers.pdf_schema import WardSchema
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000010"
WARD_CODE = draymed.codes.code_from_name("ward", category="location")


class WardReportsMessage(Schema):
    start_date = fields.String(required=True)
    end_date = fields.String(required=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Generate SEND ward reports PDFs for each location
    - Routing Key: dhos.DM000010
    - Body: Object containing a start date and an end date.
    - Notes: Generates ward report PDFs and also exports to DEA.
    - Endpoint(s):
      - GET /dhos-locations/dhos/v1/location/search
      - GET /dhos-aggregator/dhos/v1/send_ward_report_data
      - POST /dhos-pdf/dhos/v1/ward_report
      - POST /dea/ingest/v2/dhos_data (external)
    """
    logger.info("Received 'aggregate SEND ward reports' message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Aggregate SEND ward reports message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    ward_reports_message: Dict = validate_message_body_dict(
        body=body, schema=WardReportsMessage
    )

    # Get locations from Services API.
    ward_location_uuids: Set[str] = set(
        locations_api.get_locations(location_types=[WARD_CODE])
    )

    logger.debug(
        "Found %d locations for which to generate ward reports",
        len(ward_location_uuids),
    )
    for location_uuid in ward_location_uuids:
        logger.debug("Aggregating SEND ward report data for location %s", location_uuid)
        try:
            aggregated_data: Dict = aggregator_api.aggregate_send_ward_report_data(
                location_uuid=location_uuid,
                start_date=ward_reports_message["start_date"],
                end_date=ward_reports_message["end_date"],
            )
        except (RequeueMessageError, RejectMessageError):
            logger.exception("Failed to gather data for location %s", location_uuid)
            continue
        try:
            WardSchema().load(aggregated_data)
            ExportMessage().load(aggregated_data)
        except ValidationError:
            logger.exception(
                "Failed to validate aggregator response for location %s", location_uuid
            )
            continue

        # Post aggregated data to PDF API.
        logger.info("Generating ward report PDF for location %s", location_uuid)
        pdf_api.post_ward_pdf(message_body=aggregated_data)

        # Post ward report data to DEA Ingest API.
        logger.info("Exporting ward report to DEA for location %s", location_uuid)
        export_payload: Dict = dea_ingest.generate_dea_ingest_payload(
            export_data=aggregated_data, data_type="ward_report"
        )
        dea_ingest_api.post_to_dea_ingest(export_data=export_payload)
