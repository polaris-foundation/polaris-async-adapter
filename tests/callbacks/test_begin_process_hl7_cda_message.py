import json

import pytest
from _pytest.logging import LogCaptureFixture
from requests_mock import Mocker

from dhos_async_adapter.callbacks import begin_process_hl7_cda_message
from dhos_async_adapter.helpers.exceptions import RejectMessageError


class TestBeginProcessHl7CDAMessage:
    def test_process_cda_message(self, requests_mock: Mocker) -> None:
        url = f"http://dhos-connector/dhos/v1/cda_message"
        connector_post = requests_mock.post(url, text="", status_code=201)
        message = json.dumps({"content": "some XML here"})

        begin_process_hl7_cda_message.process(message)
        assert connector_post.call_count == 1

    @pytest.mark.parametrize(
        "message,error",
        [
            ("not json!", "Couldn't load message body"),
            ("{}", "Failed to validate message body"),
        ],
    )
    def test_process_invalid_message(
        self, caplog: LogCaptureFixture, message: str, error: str
    ) -> None:
        with pytest.raises(RejectMessageError):
            begin_process_hl7_cda_message.process(message)
        assert error in caplog.text
