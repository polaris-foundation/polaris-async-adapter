import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import audit_event
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestAuditEvent:
    @pytest.fixture
    def mock_audit_post(self, requests_mock: Mocker) -> Mock:
        return requests_mock.post("http://dhos-audit/dhos/v2/event")

    @pytest.fixture
    def audit_message(self) -> Dict:
        return {
            "event_type": "some_event_type",
            "event_data": {
                "some_field": "some_value",
                "some_other_field": "Some other value",
            },
        }

    def test_process_success(self, mock_audit_post: Mock, audit_message: Dict) -> None:
        # Arrange
        message_body = json.dumps(audit_message)

        # Act
        audit_event.process(message_body)

        # Assert
        assert mock_audit_post.call_count == 1
        assert mock_audit_post.last_request.json() == audit_message

    def test_process_invalid_body(self, mock_audit_post: Mock) -> None:
        # Arrange
        message_body = json.dumps({"not": "valid"})

        # Act
        with pytest.raises(RejectMessageError):
            audit_event.process(message_body)

        # Assert
        assert mock_audit_post.call_count == 0

    def test_process_bad_response(
        self, requests_mock: Mocker, audit_message: Dict
    ) -> None:
        # Arrange
        message_body = json.dumps(audit_message)
        mock_audit_post: Mock = requests_mock.post(
            "http://dhos-audit/dhos/v2/event", status_code=400
        )

        # Act
        with pytest.raises(RejectMessageError):
            audit_event.process(message_body)

        # Assert
        assert mock_audit_post.call_count == 1
