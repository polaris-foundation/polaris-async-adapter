import logging.config
from typing import List

import kombu_batteries_included
from kombu import Connection, Exchange, Queue, binding
from she_logging import logger

from dhos_async_adapter.consumer import GenericConsumer
from dhos_async_adapter.helpers.routing import (
    QUEUE_MODES,
    ROUTES_TO_UNBIND,
    ROUTING_TABLE,
)

# Change AMQP logging level to stop heartbeats being logged.
logging.getLogger("amqp").setLevel("INFO")

TASK_EXCHANGE_NAME = "dhos"
TASK_EXCHANGE_TYPE = "topic"
RETRY_EXCHANGE_NAME = "dhos-retry"
RETRY_EXCHANGE_TYPE = "fanout"
RETRY_QUEUE_NAME = "retry"
DLX_EXCHANGE_NAME = "dhos-dlx"
DLX_EXCHANGE_TYPE = "fanout"
ERROR_QUEUE_NAME = "errors"


def run() -> None:
    kombu_batteries_included.init()
    conn = Connection(kombu_batteries_included.get_connection_string())
    task_exchange: Exchange = kombu_batteries_included.infra.get_task_exchange(conn)
    logger.info("Initialising task queues")
    queues: List[Queue] = _init_task_queues(conn, task_exchange)
    logger.info("Unbinding deprecated routes")
    for queue_name, routing_keys in ROUTES_TO_UNBIND.items():
        for routing_key in routing_keys:
            queue: Queue = next(q for q in queues if q.name == queue_name)
            logger.debug("Unbind %s from %s", routing_key, queue.name)
            queue.declare()
            queue.unbind_from(task_exchange, routing_key)

    logger.info("Starting consumers")
    GenericConsumer(connection=conn, queues=queues).run()


def _init_task_queues(conn: Connection, task_exchange: Exchange) -> List[Queue]:
    return [
        Queue(
            k,
            bindings=[binding(task_exchange, routing_key=k) for k in v.keys()],
            durable=True,
            channel=conn,
            exchange=task_exchange,
            queue_arguments={
                "x-dead-letter-exchange": DLX_EXCHANGE_NAME,
            }
            if QUEUE_MODES.get(k, None) is None
            else {
                "x-dead-letter-exchange": DLX_EXCHANGE_NAME,
                "x-queue-mode": QUEUE_MODES[k],
            },
        )
        for k, v in ROUTING_TABLE.items()
    ]
