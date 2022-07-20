import pytest
import requests
from mock import Mock
from requests_mock import Mocker

from dhos_async_adapter import clients
from dhos_async_adapter.helpers.exceptions import (
    RejectMessageError,
    RequeueMessageError,
)


class TestClients:
    def test_do_request_no_connection(self, requests_mock: Mocker) -> None:
        # Arrange
        url = "http://some.url"
        payload = {"some": "payload"}
        mock_post: Mock = requests_mock.post(url, exc=requests.ConnectionError)

        # Act
        with pytest.raises(RequeueMessageError):
            clients.do_request(url=url, method="post", payload=payload)

        # Assert
        assert mock_post.call_count == 1
        assert mock_post.last_request.json() == payload

    def test_do_request_bad_response(self, requests_mock: Mocker) -> None:
        # Arrange
        url = "http://some.url"
        payload = {"some": "payload"}
        mock_post: Mock = requests_mock.post(url, status_code=404)

        # Act
        with pytest.raises(RejectMessageError):
            clients.do_request(url=url, method="post", payload=payload)

        # Assert
        assert mock_post.call_count == 1
        assert mock_post.last_request.json() == payload

    def test_do_request_exceptions(self, requests_mock: Mocker) -> None:
        # Arrange
        url = "http://some.url"
        payload = {"some": "payload"}
        mock_post: Mock = requests_mock.post(
            url, exc=requests.exceptions.ContentDecodingError
        )

        # Act
        with pytest.raises(RequeueMessageError):
            clients.do_request(url=url, method="post", payload=payload)

        # Assert
        assert mock_post.call_count == 1
        assert mock_post.last_request.json() == payload

    def test_do_request_exception_requeue(self, requests_mock: Mocker) -> None:
        # Arrange
        url = "http://some.url"
        payload = {"some": "payload"}
        mock_post: Mock = requests_mock.post(url, status_code=503)

        # Act
        with pytest.raises(RequeueMessageError):
            clients.do_request(url=url, method="post", payload=payload)

        # Assert
        assert mock_post.call_count == 1
        assert mock_post.last_request.json() == payload
