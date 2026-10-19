"""ПР5, задание 1 — поставщик (простейшая схема P -> очередь -> C).

Запуск:  python producer.py <вариант 1|2|3> [текст сообщения]
  1 — эксклюзивная очередь (её объявляет потребитель, поставщик только публикует);
  2 — очередь, сохраняемая при перезапуске RabbitMQ (durable + persistent-сообщения);
  3 — автоудаляемая очередь (auto_delete).
"""
import sys
import os

import pika

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, QUEUE_PREFIX  # noqa: E402

VARIANTS = {
    '1': {'suffix': 'exclusive', 'declare': None},
    '2': {'suffix': 'durable', 'declare': {'durable': True}},
    '3': {'suffix': 'autodelete', 'declare': {'auto_delete': True}},
}


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else '2'
    text = ' '.join(sys.argv[2:]) or 'Заказ создан: тормозные колодки x2'
    cfg = VARIANTS[variant]
    queue_name = f'{QUEUE_PREFIX}_{cfg["suffix"]}'

    connection = connect()
    channel = connection.channel()

    # Эксклюзивную очередь может объявить только соединение-владелец (потребитель),
    # поэтому в варианте 1 поставщик её не объявляет, а сразу публикует сообщение.
    if cfg['declare'] is not None:
        channel.queue_declare(queue=queue_name, **cfg['declare'])

    properties = None
    if variant == '2':
        properties = pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)

    channel.basic_publish(exchange='', routing_key=queue_name, body=text.encode(),
                          properties=properties)
    print(f'SENT to {queue_name}: {text}')
    connection.close()


if __name__ == '__main__':
    main()
