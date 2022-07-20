import uuid
from pathlib import Path
from typing import AnyStr, Callable, List, Optional, Type

from kombu import Connection, Consumer, Message, Queue
from kombu.mixins import ConsumerMixin
from kombu.transport.pyamqp import Channel
from she_logging import logger
from she_logging.request_id import current_request_id, reset_request_id, set_request_id

from dhos_async_adapter.helpers.exceptions import (
    RejectMessageError,
    RequeueMessageError,
)
from dhos_async_adapter.helpers.routing import CALLBACK_LOOKUP

# This presence of this file is used to signal to Prometheus that the connection to RabbitMQ is alive.
alive_file: Path = Path(__file__).parent.parent / "alive.txt"


class GenericConsumer(ConsumerMixin):
    def __init__(self, connection: Connection, queues: List[Queue]) -> None:
        logger.debug("Initialising generic consumer")
        self.connection = connection
        self.queues = queues

    def get_consumers(self, consumer_cls: Type, channel: Channel) -> List[Consumer]:
        return [
            consumer_cls(
                queues=self.queues, callbacks=[self.on_message], accept=["json"]
            )
        ]

    def on_connection_error(self, exc: Type[Exception], interval: int) -> None:
        logger.error("ConsumerMixin.on_connection_error called")
        alive_file.unlink(missing_ok=True)
        return super(GenericConsumer, self).on_connection_error(exc, interval)

    def on_connection_revived(self) -> None:
        logger.info("ConsumerMixin.on_connection_revived called")
        alive_file.touch(exist_ok=True)
        return super(GenericConsumer, self).on_connection_revived()

    def on_message(self, body: AnyStr, message: Message) -> None:
        """Callback for messages."""
        correlation_id: Optional[str] = message.properties.get("correlation_id", None)
        if correlation_id is None:
            correlation_id = current_request_id() or str(uuid.uuid4())
        request_id_token = set_request_id(correlation_id)

        routing_key: Optional[str] = message.delivery_info.get("routing_key")
        if routing_key is None or routing_key not in CALLBACK_LOOKUP:
            logger.error("Received message with unknown routing key '%s'", routing_key)
            message.reject()
            return

        callback_method: Callable[[AnyStr], None] = CALLBACK_LOOKUP[routing_key]
        # noinspection PyBroadException
        try:
            callback_method(body)
            logger.info("Successfully processed message (%s)", routing_key)
            message.ack()
        except RequeueMessageError:
            logger.error("Requeueing message (%s)", routing_key)
            message.requeue()
        except RejectMessageError:
            logger.error("Rejecting message (%s)", routing_key)
            message.reject()
        except Exception:
            logger.exception("Exception while processing message (%s)", routing_key)
            message.reject()
        finally:
            reset_request_id(request_id_token)
