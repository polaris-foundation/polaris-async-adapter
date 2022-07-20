from typing import AnyStr, Dict

from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from she_logging import logger

from dhos_async_adapter.clients import notifications_api
from dhos_async_adapter.helpers.validation import validate_message_body_dict

ROUTING_KEY = "dhos.DM000017"


class EmailNotificationRequest(Schema):

    email_address = fields.String(
        required=True, description="Email address", example="john.roberts@mail.com"
    )
    email_type = fields.String(
        required=True,
        description="Email type",
        validate=OneOf(["WELCOME_EMAIL"]),
        example="WELCOME_EMAIL",
    )


def process(body: AnyStr) -> None:
    """
    - Summary: Sends an email message.
    - Routing Key: dhos.DM000017
    - Body: Details of an email message.
    - Notes: Includes message type and email address.
    - Endpoint(s): POST /dhos-notifications/dhos/v1/email
    """
    logger.info("Received 'send email' message (%s)", ROUTING_KEY)

    email_details: Dict = validate_message_body_dict(
        body=body, schema=EmailNotificationRequest
    )

    # Post message to Notifications API.
    notifications_api.create_email(email_details=email_details)
