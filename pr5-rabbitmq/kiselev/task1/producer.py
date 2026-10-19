"""ПР5, задание 1 — поставщик (Киселев К.С., тема: отзывы и рейтинг).

Вариант 3: автоудаляемая очередь (auto_delete=True).
Запуск:  python producer.py [текст сообщения]
"""
import os
import sys

import pika

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 3
QUEUE = PREFIX
QUEUE_ARGS = {'auto_delete': True}
DEFAULT_TEXT = 'Новый отзыв: оценка 5, продавец 42'


def main() -> None:
    text = ' '.join(sys.argv[1:]) or DEFAULT_TEXT
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, **QUEUE_ARGS)
    channel.basic_publish(exchange='', routing_key=QUEUE, body=text.encode())
    print(f'SENT to {QUEUE}: {text}')
    connection.close()


if __name__ == '__main__':
    main()
