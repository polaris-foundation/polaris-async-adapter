import json
from typing import Dict

import pytest
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter import config
from dhos_async_adapter.callbacks import generate_ward_reports


class TestGenerateWardReports:
    @pytest.fixture
    def mock_get_locations(self, requests_mock: Mocker, location_uuid: str) -> Mock:
        return requests_mock.get(
            f"http://dhos-locations/dhos/v1/location/search?location_types"
            f"={generate_ward_reports.WARD_CODE}&compact=True",
            json={
                location_uuid: {
                    "uuid": location_uuid,
                    "location_type": generate_ward_reports.WARD_CODE,
                }
            },
        )

    @pytest.fixture
    def mock_aggregate_data(
        self, requests_mock: Mocker, ward_report_pdf_data: Dict, location_uuid: str
    ) -> Mock:
        return requests_mock.get(
            f"http://dhos-aggregator/dhos/v1/send_ward_report_data?location_uuid={location_uuid}",
            json=ward_report_pdf_data,
        )

    @pytest.fixture
    def mock_post_ward_report(self, requests_mock: Mocker) -> Mock:
        return requests_mock.post(
            "http://dhos-pdf/dhos/v1/ward_report", status_code=201
        )

    @pytest.fixture
    def aggregate_message(self) -> Dict:
        return {
            "start_date": "2019-01-01T00:00:00.000Z",
            "end_date": "2019-02-01T00:00:00.000Z",
        }

    @pytest.mark.parametrize(
        "aggregator_response",
        [
            {
                "hospital_name": "something",
                "ward_name": "otherthing",
                "report_month": "April",
                "report_year": "2019",
            },
            {
                "pdf_data": {},
                "hospital_name": "something",
                "report_month": "April",
                "report_year": "2019",
            },
            {
                "pdf_data": {},
                "hospital_name": "something",
                "ward_name": "otherthing",
                "report_year": "2019",
            },
            {
                "pdf_data": {},
                "hospital_name": "something",
                "ward_name": "otherthing",
                "report_month": "April",
            },
            {
                "hospital_name": "something",
                "ward_name": "otherthing",
                "report_month": "April",
                "report_year": "2019",
            },
        ],
    )
    def test_completes_with_invalid_json(
        self,
        requests_mock: Mocker,
        mock_get_locations: Mock,
        aggregate_message: Dict,
        aggregator_response: Dict,
        location_uuid: str,
    ) -> None:
        message_body = json.dumps(aggregate_message)
        requests_mock.get(
            f"http://dhos-aggregator/dhos/v1/send_ward_report_data?location_uuid={location_uuid}",
            json=aggregator_response,
        )
        generate_ward_reports.process(message_body)
        assert mock_get_locations.call_count == 1

    @pytest.mark.freeze_time("2020-01-01T00:00:00.000+00:00")
    def test_process_success(
        self,
        mock_post_ward_report: Mock,
        mock_get_locations: Mock,
        mock_aggregate_data: Mock,
        mock_dea_ingest_post: Mock,
        mock_retrieve_dea_auth0_jwt: Mock,
        aggregate_message: Dict,
        ward_report_pdf_data: Dict,
        location_uuid: str,
    ) -> None:
        # Arrange
        message_body = json.dumps(aggregate_message)

        # Act
        generate_ward_reports.process(message_body)

        # Assert
        assert mock_get_locations.call_count == 1
        assert mock_aggregate_data.call_count == 1
        assert location_uuid in mock_aggregate_data.last_request.url
        assert mock_post_ward_report.call_count == 1
        assert mock_retrieve_dea_auth0_jwt.call_count == 1
        assert mock_dea_ingest_post.call_count == 1
        assert (
            mock_dea_ingest_post.last_request.headers["Authorization"] == "Bearer TOKEN"
        )
        actual_body = mock_dea_ingest_post.last_request.json()
        assert actual_body["data"] == ward_report_pdf_data
        assert actual_body["metadata"] == {
            "data_source": "dhos_async_adapter.helpers.dea_ingest",
            "data_type": "ward_report",
            "customer": config.CUSTOMER_CODE,
            "environment": config.ENVIRONMENT,
            "circle_tag": config.BUILD_CIRCLE_TAG,
            "git_tag": config.BUILD_GIT_TAG,
            "created": "2020-01-01T00:00:00+00:00",
            "num_records": len(ward_report_pdf_data),
        }
