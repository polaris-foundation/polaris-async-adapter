import json

import pytest
from marshmallow import Schema, fields

from dhos_async_adapter.helpers import validation
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class DummySchema(Schema):
    dummy = fields.String(required=True)


class TestValidation:
    def test_validate_message_body_dict_success(self) -> None:
        message_body = json.dumps({"dummy": "field", "extra": "field"})
        validated = validation.validate_message_body_dict(
            message_body, schema=DummySchema
        )
        assert validated == {"dummy": "field"}

    def test_validate_message_body_dict_failure(self) -> None:
        message_body = json.dumps({"not": "matching"})
        with pytest.raises(RejectMessageError):
            validation.validate_message_body_dict(message_body, schema=DummySchema)

    def test_validate_message_body_dict_not_json_body(self) -> None:
        message_body = b"not json"
        with pytest.raises(RejectMessageError):
            validation.validate_message_body_dict(message_body, schema=DummySchema)

    def test_validate_message_body_list_success(self) -> None:
        message_body = json.dumps(
            [
                {"dummy": "field", "extra": "field"},
                {"dummy": "field2", "extra": "field"},
            ]
        )
        validated = validation.validate_message_body_list(
            message_body, schema=DummySchema
        )
        assert validated == [{"dummy": "field"}, {"dummy": "field2"}]

    def test_validate_message_body_list_failure(self) -> None:
        message_body = json.dumps([{"not": "matching"}])
        with pytest.raises(RejectMessageError):
            validation.validate_message_body_list(message_body, schema=DummySchema)

    def test_validate_message_body_list_not_json_body(self) -> None:
        message_body = b"not json"
        with pytest.raises(RejectMessageError):
            validation.validate_message_body_list(message_body, schema=DummySchema)
