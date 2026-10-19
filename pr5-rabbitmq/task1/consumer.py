"""ПР5, задание 1 — потребитель.

Запуск:  python consumer.py <вариант 1|2|3>
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, QUEUE_PREFIX  # noqa: E402

VARIANTS = {
    '1': {'suffix': 'exclusive', 'declare': {'exclusive': True}},
    '2': {'suffix': 'durable', 'declare': {'durable': True}},
    '3': {'suffix': 'autodelete', 'declare': {'auto_delete': True}},
}


def process_message(channel, method, properties, body: bytes) -> None:
    print(f'RECEIVED: {body.decode()}')
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else '2'
    cfg = VARIANTS[variant]
    queue_name = f'{QUEUE_PREFIX}_{cfg["suffix"]}'

    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, **cfg['declare'])
    channel.basic_consume(queue=queue_name, on_message_callback=process_message)

    print(f'Waiting for messages in {queue_name} (variant {variant})... CTRL+C to exit')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
