import json
import uuid
from contextvars import Token
from pathlib import Path
from typing import Generator

import pytest
from kombu import Connection, Message
from mock import MagicMock, Mock
from pytest_mock import MockFixture

from dhos_async_adapter import consumer
from dhos_async_adapter.consumer import GenericConsumer
from dhos_async_adapter.helpers.exceptions import (
    RejectMessageError,
    RequeueMessageError,
)


@pytest.mark.usefixtures("mock_get_request_headers")
class TestAudit:
    def test_on_message_success(self, mocker: MockFixture) -> None:
        # Arrange
        routing_key = "dhos.34837004"
        mock_callback = MagicMock(__name__="mock_callback")
        mocker.patch.dict(consumer.CALLBACK_LOOKUP, {routing_key: mock_callback})
        message_body = {"key": "value"}
        message: Message = Message(
            body=message_body, delivery_info={"routing_key": routing_key}
        )
        mock_ack: Mock = mocker.patch.object(Message, "ack")
        generic_consumer = GenericConsumer(Connection(), [])

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_callback.call_count == 1
        assert mock_ack.call_count == 1

    def test_on_message_requeue(self, mocker: MockFixture) -> None:
        # Arrange
        routing_key = "dhos.34837004"
        mock_callback = MagicMock(
            __name__="mock_callback", side_effect=RequeueMessageError
        )
        mocker.patch.dict(consumer.CALLBACK_LOOKUP, {routing_key: mock_callback})
        message_body = {"key": "value"}
        generic_consumer = GenericConsumer(Connection(), [])
        message: Message = Message(
            body=message_body, delivery_info={"routing_key": routing_key}
        )
        mock_requeue: Mock = mocker.patch.object(message, "requeue")

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_callback.call_count == 1
        assert mock_requeue.call_count == 1

    def test_on_message_reject(self, mocker: MockFixture) -> None:
        # Arrange
        routing_key = "dhos.34837004"
        mock_callback = MagicMock(
            __name__="mock_callback", side_effect=RejectMessageError
        )
        mocker.patch.dict(consumer.CALLBACK_LOOKUP, {routing_key: mock_callback})
        message_body = {"key": "value"}
        generic_consumer = GenericConsumer(Connection(), [])
        message: Message = Message(
            body=message_body, delivery_info={"routing_key": routing_key}
        )
        mock_reject: Mock = mocker.patch.object(message, "reject")

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_callback.call_count == 1
        assert mock_reject.call_count == 1

    def test_on_message_unexpected_error(self, mocker: MockFixture) -> None:
        # Arrange
        routing_key = "dhos.34837004"
        mock_callback = MagicMock(__name__="mock_callback", side_effect=Exception)
        mocker.patch.dict(consumer.CALLBACK_LOOKUP, {routing_key: mock_callback})
        message_body = {"key": "value"}
        generic_consumer = GenericConsumer(Connection(), [])
        message: Message = Message(
            body=message_body, delivery_info={"routing_key": routing_key}
        )
        mock_reject: Mock = mocker.patch.object(message, "reject")

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_callback.call_count == 1
        assert mock_reject.call_count == 1

    def test_on_message_unknown_routing_key(self, mocker: MockFixture) -> None:
        # Arrange
        routing_key = "unknown"
        message_body = {"key": "value"}
        generic_consumer = GenericConsumer(Connection(), [])
        message: Message = Message(
            body=message_body, delivery_info={"routing_key": routing_key}
        )
        mock_reject: Mock = mocker.patch.object(message, "reject")

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_reject.call_count == 1

    def test_on_message_request_id(self, mocker: MockFixture) -> None:
        # Arrange
        correlation_id = str(uuid.uuid4())
        mock_token = Mock(spec=Token)
        routing_key = "dhos.34837004"
        mock_callback = MagicMock(__name__="mock_callback")
        mocker.patch.dict(consumer.CALLBACK_LOOKUP, {routing_key: mock_callback})
        message_body = {"key": "value"}
        message: Message = Message(
            body=message_body,
            delivery_info={"routing_key": routing_key},
            properties={"correlation_id": correlation_id},
        )
        mock_ack: Mock = mocker.patch.object(Message, "ack")
        generic_consumer = GenericConsumer(Connection(), [])
        mock_set_request_id: Mock = mocker.patch.object(
            consumer, "set_request_id", return_value=mock_token
        )
        mock_reset_request_id: Mock = mocker.patch.object(consumer, "reset_request_id")

        # Act
        generic_consumer.on_message(json.dumps(message_body), message)

        # Assert
        assert mock_ack.call_count == 1
        assert mock_set_request_id.call_count == 1
        mock_set_request_id.assert_called_with(correlation_id)
        assert mock_reset_request_id.call_count == 1
        mock_reset_request_id.assert_called_with(mock_token)

    @pytest.fixture
    def alive_file(self) -> Generator[Path, None, None]:
        """Fixture for the liveness file. Will restore the pre-test state afterwards."""
        alive_file: Path = Path(__file__).parent.parent / "alive.txt"
        pre_existing: bool = alive_file.exists()
        yield alive_file
        if pre_existing:
            alive_file.touch(exist_ok=True)
        if not pre_existing:
            alive_file.unlink(missing_ok=True)

    def test_on_connection_revived(self, alive_file: Path) -> None:
        generic_consumer = GenericConsumer(Connection(), [])
        assert not alive_file.exists()
        generic_consumer.on_connection_revived()
        assert alive_file.exists()

    def test_on_connection_error(self, alive_file: Path) -> None:
        alive_file.touch(exist_ok=True)
        generic_consumer = GenericConsumer(Connection(), [])
        assert alive_file.exists()
        generic_consumer.on_connection_error(Exception, 1)
        assert not alive_file.exists()
