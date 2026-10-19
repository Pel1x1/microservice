"""ПР5, задание 2 — поставщик задач (Начинкин И.С.: пересчёт итогов по заказам).

Вариант 1: fanout-обменник, символ сна '#'.
Запуск:  python producer.py [routing_key] [текст задачи]   (для fanout ключ игнорируется)
Каждый символ '#' в тексте = 1 секунда работы воркера.
"""
import os
import sys

import pika

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 1: символ сна '#', обменник fanout, сохранение при перезапуске: да
SLEEP_CHAR = '#'
EXCHANGE_TYPE = 'fanout'
PERSISTENT = True
EXCHANGE = PREFIX + '_tasks'
QUEUE = PREFIX + '_tasks_queue'
DEFAULT_KEY = ''
DEFAULT_TEXT = 'Пересчёт итогов по заказу 1042 ###'


def main() -> None:
    routing_key = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_KEY
    text = ' '.join(sys.argv[2:]) or DEFAULT_TEXT
    connection = connect()
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=PERSISTENT)
    properties = None
    if PERSISTENT:
        properties = pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
    channel.basic_publish(exchange=EXCHANGE, routing_key=routing_key, body=text.encode(),
                          properties=properties)
    print(f'SENT [{EXCHANGE}, key="{routing_key}"]: {text}')
    connection.close()


if __name__ == '__main__':
    main()
