import json
from typing import Dict, List

import pytest
from mock import Mock

from dhos_async_adapter import config
from dhos_async_adapter.callbacks import export_gdm_syne_bg_readings


class TestExportGdmSyneBgReadings:
    @pytest.fixture
    def export_gdm_syne_bg_readings_message(self) -> List[Dict]:
        return [
            {
                "reading_id": "5d505813-1152-4466-945e-9ef1d09c1e55",
                "patient_id": "011a35d9-f0ab-44f6-85b4-397d1f4d593f",
                "bg_reading_datetime": "2020-04-27T14:16:25.474Z",
                "prandial_tag": "other",
                "blood_glucose_value": 3.0,
                "meds_taken_flag": False,
                "sct_code": ["11687002"],
                "first_bg_reading_pre_seven_days_flag": False,
            },
            {
                "reading_id": "0f4f250f-36f7-407a-8b92-42757961785e",
                "patient_id": "011a35d9-f0ab-44f6-85b4-397d1f4d593f",
                "bg_reading_datetime": "2020-04-25T14:16:27.395Z",
                "prandial_tag": "other",
                "blood_glucose_value": 3.0,
                "meds_taken_flag": False,
                "sct_code": ["11687002"],
                "first_bg_reading_pre_seven_days_flag": False,
            },
        ]

    @pytest.mark.freeze_time("2020-01-01T00:00:00.000+00:00")
    def test_process_success(
        self,
        mock_dea_ingest_post: Mock,
        mock_retrieve_dea_auth0_jwt: Mock,
        export_gdm_syne_bg_readings_message: Dict,
    ) -> None:
        # Arrange
        message_body = json.dumps(export_gdm_syne_bg_readings_message)

        # Act
        export_gdm_syne_bg_readings.process(message_body)

        # Assert
        assert mock_retrieve_dea_auth0_jwt.call_count == 1
        assert mock_dea_ingest_post.call_count == 1
        assert (
            mock_dea_ingest_post.last_request.headers["Authorization"] == "Bearer TOKEN"
        )
        actual_body = mock_dea_ingest_post.last_request.json()
        assert actual_body["data"] == export_gdm_syne_bg_readings_message
        assert actual_body["metadata"] == {
            "data_source": "dhos_async_adapter.helpers.dea_ingest",
            "data_type": "syne_bg_readings",
            "customer": config.CUSTOMER_CODE,
            "environment": config.ENVIRONMENT,
            "circle_tag": config.BUILD_CIRCLE_TAG,
            "git_tag": config.BUILD_GIT_TAG,
            "created": "2020-01-01T00:00:00+00:00",
            "num_records": 2,
        }
