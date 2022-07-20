import json
import uuid
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import bg_reading_abnormal
from dhos_async_adapter.helpers.exceptions import RejectMessageError


@pytest.mark.usefixtures("mock_get_request_headers")
class TestBgReadingAbnormal:
    @pytest.fixture
    def reading_uuid(self) -> str:
        return str(uuid.uuid4())

    @pytest.fixture
    def abnormal_reading_message(self, reading_uuid: str) -> Dict:
        return {"uuid": reading_uuid}

    @pytest.fixture
    def mock_process_reading_post(
        self, requests_mock: Mocker, reading_uuid: str
    ) -> Mock:
        return requests_mock.post(
            f"http://gdm-bg-readings/gdm/v1/process_alerts/reading/{reading_uuid}",
            json={"status": "sent"},
        )

    def test_process_success(
        self, mock_process_reading_post: Mock, abnormal_reading_message: Dict
    ) -> None:
        # Arrange
        message_body = json.dumps(abnormal_reading_message)

        # Act
        bg_reading_abnormal.process(message_body)

        # Assert
        assert mock_process_reading_post.call_count == 1

    def test_process_invalid_body(self, mock_process_reading_post: Mock) -> None:
        # Arrange
        message_body = json.dumps({"not": "valid"})

        # Act
        with pytest.raises(RejectMessageError):
            bg_reading_abnormal.process(message_body)

        # Assert
        assert mock_process_reading_post.call_count == 0

    def test_process_bad_response(
        self, requests_mock: Mocker, abnormal_reading_message: Dict, reading_uuid: str
    ) -> None:
        # Arrange
        message_body: str = json.dumps(abnormal_reading_message)
        mock_process_reading_post: Mock = requests_mock.post(
            f"http://gdm-bg-readings/gdm/v1/process_alerts/reading/{reading_uuid}",
            status_code=400,
        )

        # Act
        with pytest.raises(RejectMessageError):
            bg_reading_abnormal.process(message_body)

        # Assert
        assert mock_process_reading_post.call_count == 1
