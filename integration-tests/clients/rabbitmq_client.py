import logging
import uuid
from typing import Dict, Generator, Optional

from behave import fixture
from behave.runner import Context
from environs import Env
from kombu import Connection, Exchange, Message, Producer, Queue
from kombu.simple import SimpleQueue

logger = logging.getLogger("Tests")


@fixture
def create_rabbitmq_connection(context: Context) -> Generator[Connection, None, None]:
    env = Env()
    host: str = env.str("RABBITMQ_HOST")
    port: int = env.int("RABBITMQ_PORT", 5672)
    username: str = env.str("RABBITMQ_USERNAME")
    password: str = env.str("RABBITMQ_PASSWORD")
    conn_string: str = f"amqp://{username}:{password}@{host}:{port}//"
    context.rabbitmq_connection = Connection(conn_string)
    context.rabbitmq_exchange = Exchange(
        "dhos", "topic", channel=context.rabbitmq_connection
    )

    yield context.rabbitmq_connection
    context.rabbitmq_connection.release()
    del context.rabbitmq_exchange
    del context.rabbitmq_connection


@fixture
def create_rabbitmq_dlx_exchange(context: Context) -> Generator[None, None, None]:
    connection = context.rabbitmq_connection
    context.rabbitmq_error_exchange = Exchange("dhos-dlx", "fanout", channel=connection)
    context.rabbitmq_error_queue = Queue(
        "errors", exchange=context.rabbitmq_error_exchange, channel=connection
    )
    context.rabbitmq_error_queue.declare()
    yield
    # Purge queue after test
    SimpleQueue(context.rabbitmq_connection, context.rabbitmq_error_queue).clear()


@fixture
def create_rabbitmq_queues(
    context: Context, routing_keys: Dict[str, str]
) -> Generator[Dict[str, SimpleQueue], None, None]:
    connection = context.rabbitmq_connection
    exchange = context.rabbitmq_exchange
    context.rabbitmq_queues = {}
    for routing_key, queue_name in routing_keys.items():
        queue = Queue(
            queue_name,
            exchange=exchange,
            routing_key=routing_key,
            channel=connection,
            queue_arguments={"x-dead-letter-exchange": "dhos-dlx"},
        )
        queue.declare()
        context.rabbitmq_queues[routing_key] = queue
    yield context.rabbitmq_queues

    # Purge queues after test
    for queue in context.rabbitmq_queues.values():
        SimpleQueue(context.rabbitmq_connection, queue).clear()


def publish_message(
    connection: Connection,
    exchange: Exchange,
    message: str,
    routing_key: str,
    message_identifier: Optional[str] = None,
) -> None:
    logger.debug("Publishing message with routing key %s", routing_key)
    with connection as conn:
        producer: Producer = conn.Producer(serializer="json")
        producer.publish(
            body=message,
            exchange=exchange,
            routing_key=routing_key,
            content_type="application/text",
            retry=True,
            headers={"x-message-identifier": message_identifier or str(uuid.uuid4())},
        )


def get_message_on_queue(queue: Queue, context: Context) -> Message:
    simple_queue: SimpleQueue = SimpleQueue(context.rabbitmq_connection, queue)
    message: Message = simple_queue.get(block=True, timeout=10)
    message.ack()
    return message


def get_first_message_on_queue_with_routing_key(
    queue: Queue, routing_key: str, context: Context
) -> Message:
    logger.debug("Looking for message with routing key %s", routing_key)
    simple_queue: SimpleQueue = SimpleQueue(context.rabbitmq_connection, queue)
    while True:
        message: Message = simple_queue.get(block=True, timeout=10)
        message.ack()
        message_routing_key: Optional[str] = message.delivery_info.get("routing_key")
        if message_routing_key == routing_key:
            logger.debug("Found message with routing key %s", routing_key)
            return message
        logger.debug("Skipping message with routing key %s", message_routing_key)
