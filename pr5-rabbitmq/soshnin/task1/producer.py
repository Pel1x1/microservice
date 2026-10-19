"""ПР5, задание 1 — поставщик (Сошнин Н.А., тема: передача посылок в доставку).

Вариант 1: эксклюзивная очередь (exclusive=True).
Запуск:  python producer.py [текст сообщения]
"""
import os
import sys

import pika

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 1
QUEUE = PREFIX
DEFAULT_TEXT = 'Посылка 8841 передана в службу доставки'


def main() -> None:
    text = ' '.join(sys.argv[1:]) or DEFAULT_TEXT
    connection = connect()
    channel = connection.channel()
    # Эксклюзивную очередь может объявить только соединение-владелец (потребитель).
    # Поставщик её НЕ объявляет (иначе RESOURCE_LOCKED), а сразу публикует.
    channel.basic_publish(exchange='', routing_key=QUEUE, body=text.encode())
    print(f'SENT to {QUEUE}: {text}')
    connection.close()


if __name__ == '__main__':
    main()
