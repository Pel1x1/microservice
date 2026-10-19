"""ПР5, задание 1 — поставщик (Гидаятов К.Г., тема: прайс-листы продавцов).

Вариант 2: очередь, сохраняемая при перезапуске (durable=True + persistent-сообщения).
Запуск:  python producer.py [текст сообщения]
"""
import os
import sys

import pika

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 2
QUEUE = PREFIX
QUEUE_ARGS = {'durable': True}
DEFAULT_TEXT = 'Прайс-лист магазина 17 загружен на проверку'


def main() -> None:
    text = ' '.join(sys.argv[1:]) or DEFAULT_TEXT
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, **QUEUE_ARGS)
    # persistent-сообщение переживает перезапуск RabbitMQ вместе с durable-очередью
    properties = pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
    channel.basic_publish(exchange='', routing_key=QUEUE, body=text.encode(), properties=properties)
    print(f'SENT to {QUEUE}: {text}')
    connection.close()


if __name__ == '__main__':
    main()
