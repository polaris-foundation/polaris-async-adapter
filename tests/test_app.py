from typing import List

import kombu_batteries_included
import pytest
from kombu import Connection, Exchange, Queue
from mock import Mock
from pytest_mock import MockFixture

from dhos_async_adapter import app
from dhos_async_adapter.consumer import GenericConsumer
from dhos_async_adapter.helpers.routing import ROUTES_TO_UNBIND, ROUTING_TABLE


@pytest.mark.usefixtures(
    "mock_exchange_init", "mock_queue_init", "mock_connection_channel"
)
class TestApp:
    def test_run(self, mocker: MockFixture) -> None:
        # Arrange
        mock_queues: List[Mock] = []
        for queue_name in ROUTING_TABLE.keys():
            mock_queue = Mock(spec=Queue)
            mock_queue.name = queue_name
            mock_queues.append(mock_queue)
        mock_init_kbi: Mock = mocker.patch.object(kombu_batteries_included, "init")
        mock_init_task_queues: Mock = mocker.patch.object(
            app, "_init_task_queues", return_value=mock_queues
        )
        mock_audit_consumer_run: Mock = mocker.patch.object(GenericConsumer, "run")

        # Act
        app.run()

        # Assert
        assert mock_init_kbi.call_count == 1
        assert mock_init_task_queues.call_count == 1
        assert mock_audit_consumer_run.call_count == 1
        for k, v in ROUTES_TO_UNBIND.items():
            mock_queue = next(m for m in mock_queues if m.name == k)
            assert mock_queue.unbind_from.call_count == len(v)

    def test_run_connection_failure(self, mock_connection_channel: Mock) -> None:
        mock_connection_channel.side_effect = ConnectionRefusedError()
        with pytest.raises(ConnectionRefusedError):
            app.run()
        assert mock_connection_channel.call_count == 1

    def test_init_task_queues(self, mock_queue_init: Mock) -> None:
        app._init_task_queues(Connection(), Exchange())
        assert mock_queue_init.call_count == len(ROUTING_TABLE.keys())
