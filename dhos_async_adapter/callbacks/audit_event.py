from typing import AnyStr, Dict

from marshmallow import Schema, fields
from she_logging import logger

from dhos_async_adapter.clients import audit_api
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.34837004"


class AuditEvent(Schema):
    event_type = fields.String(required=True)
    event_data = fields.Dict(required=True)


def process(body: AnyStr) -> None:
    """
    - Summary: Records an audit event in the Audit API service.
    - Routing Key: dhos.34837004
    - Body: Details of the audit event.
    - Notes: This is our primary mechanism for recording specific audit events.
    - Endpoint(s): POST /dhos-audit/dhos/v2/event
    """
    logger.info("Received audit message (%s)", ROUTING_KEY)

    # Load and validate message body.
    logger.debug(
        "Audit message body (%s)",
        ROUTING_KEY,
        extra={"message_body": body},
    )
    audit_event: Dict = validate_message_body_dict(body=body, schema=AuditEvent)

    # Post event to Audit API.
    audit_api.create_audit_event(audit_event=audit_event)
