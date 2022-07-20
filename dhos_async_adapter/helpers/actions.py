from typing import Dict, Optional

from marshmallow import EXCLUDE, Schema, fields
from she_logging import logger

from dhos_async_adapter.helpers.exceptions import RejectMessageError


class ProcessMessageData(Schema):
    class Meta:
        unknown = EXCLUDE

    is_processed = fields.Boolean(required=True)


class ProcessObservationSetData(Schema):
    patient = fields.Field(required=True)
    encounter = fields.Field(required=True)
    observation_set = fields.Field(required=True)
    clinician = fields.Field(required=False)


class Action(Schema):
    name = fields.String(required=True)
    data = fields.Field(required=True)


class ActionsMessage(Schema):
    dhos_connector_message_uuid = fields.String(required=True)
    actions = fields.Nested(Action, many=True, required=True)


class HL7Message(Schema):
    message_uuid = fields.String(required=True)


class HL7CDAMessage(Schema):
    content = fields.String(required=True)


class ActionsMessageNoConnectorId(Schema):
    actions = fields.Nested(Action, many=True, required=True)


def extract_action_if_exists(message: Dict, action_name: str) -> Optional[Dict]:
    try:
        return extract_action(message, action_name)
    except RejectMessageError:
        return None


def extract_action(message: Dict, action_name: str) -> Dict:
    """
    Extracts the named action from the provided message. Some validation using
    ActionsMessage schema has already been done, so we can assume some fields
    are present.
    """
    if message.get("actions") is None:
        logger.info("No actions present in message")
        raise RejectMessageError()

    action: Optional[Dict] = next(
        (a for a in message["actions"] if a["name"] == action_name),
        None,
    )
    if action is None:
        logger.info("No action '%s' present in message", action_name)
        raise RejectMessageError()
    logger.debug(
        "Found action '%s'",
        action_name,
        extra={"action": action},
    )
    return action
