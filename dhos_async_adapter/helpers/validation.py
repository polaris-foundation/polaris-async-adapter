import json
from json import JSONDecodeError
from typing import AnyStr, Dict, List, Type

from marshmallow import EXCLUDE, Schema, ValidationError
from she_logging import logger

from dhos_async_adapter.helpers.exceptions import RejectMessageError


def validate_message_body_dict(
    body: AnyStr, schema: Type[Schema], unknown: str = EXCLUDE
) -> Dict:
    # Get message JSON body.
    try:
        contents: Dict = json.loads(body)
    except JSONDecodeError:
        logger.exception("Couldn't load message body")
        raise RejectMessageError()

    # Validate message body.
    try:
        validated_message = schema().load(contents, unknown=unknown)
    except ValidationError:
        logger.exception("Failed to validate message body")
        raise RejectMessageError()

    logger.debug("Successfully validated message body")
    return validated_message


def validate_message_body_list(
    body: AnyStr, schema: Type[Schema], unknown: str = EXCLUDE
) -> List[Dict]:
    # Get message JSON body.
    try:
        contents: List[Dict] = json.loads(body)
    except JSONDecodeError:
        logger.exception("Couldn't load message body")
        raise RejectMessageError()

    # Validate message body.
    try:
        validated_message = schema().load(contents, unknown=unknown, many=True)
    except ValidationError:
        logger.exception("Failed to validate message body")
        raise RejectMessageError()

    logger.debug("Successfully validated message body")
    return validated_message
