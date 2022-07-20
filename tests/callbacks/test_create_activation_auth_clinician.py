import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter.callbacks import create_activation_auth_clinician


@pytest.mark.usefixtures("mock_get_request_headers")
class TestCreateActivationAuthClinician:
    @pytest.fixture
    def mock_clinician_post(self, requests_mock: Mocker, clinician_uuid: str) -> Mock:
        return requests_mock.post(
            "http://dhos-activation-auth/dhos/v1/clinician",
            json={"uuid": clinician_uuid},
        )

    @pytest.fixture
    def clinician_message(self, clinician_uuid: str) -> Dict:
        return {
            "uuid": clinician_uuid,
            "send_entry_identifier": "12345",
            "contract_expiry_eod_date": "1992-06-18",
            "login_active": True,
            "products": [{"product_name": "SEND"}],
            "groups": ["SEND Superclinician"],
        }

    def test_process_success(
        self,
        mock_clinician_post: Mock,
        clinician_message: Dict,
    ) -> None:
        # Arrange
        message_body = json.dumps(clinician_message)

        # Act
        create_activation_auth_clinician.process(message_body)

        # Assert
        assert mock_clinician_post.call_count == 1
        assert mock_clinician_post.last_request.json() == {
            "clinician_id": clinician_message["uuid"],
            "send_entry_identifier": "12345",
            "contract_expiry_eod_date": "1992-06-18",
            "login_active": True,
            "products": ["SEND"],
            "groups": ["SEND Superclinician"],
        }
