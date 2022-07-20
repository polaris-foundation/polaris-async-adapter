import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import email


@pytest.mark.usefixtures("mock_get_request_headers")
class TestCreateEmailNotification:
    @pytest.fixture
    def email_valid_details(self) -> Dict:
        return {
            "email_address": "some.email@mail.com",
            "email_type": "WELCOME_EMAIL",
        }

    @pytest.fixture
    def mock_email_post(
        self, requests_mock: Mocker, email_valid_details: Dict, clinician_uuid: str
    ) -> Mock:
        return requests_mock.post(
            "http://dhos-notifications/dhos/v1/email",
            json=email_valid_details,
        )

    def test_process_success(
        self,
        mock_email_post: Mock,
        email_valid_details: Dict,
    ) -> None:
        # Arrange
        message_body = json.dumps(email_valid_details)

        # Act
        email.process(message_body)

        # Assert
        assert mock_email_post.call_count == 1
        assert mock_email_post.last_request.json() == email_valid_details
