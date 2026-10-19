"""ПР5, задание 1 — потребитель (Начинкин И.С., тема: заказы).

Вариант 1: эксклюзивная очередь (exclusive=True).
Запуск:  python consumer.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 1
QUEUE = PREFIX
QUEUE_ARGS = {'exclusive': True}


def process_message(channel, method, properties, body: bytes) -> None:
    print(f'RECEIVED: {body.decode()}')
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, **QUEUE_ARGS)
    channel.basic_consume(queue=QUEUE, on_message_callback=process_message)
    print(f'Waiting for messages in {QUEUE}... CTRL+C to exit')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
