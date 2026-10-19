"""ПР5, задание 2 — поставщик задач.

Запуск:  python producer.py <вариант> <routing_key> <текст задачи>
Примеры:
  python producer.py 1 "" "Импорт прайс-листа магазина 17 ####"
  python producer.py 2 pricelist.import "Импорт прайс-листа ***"
  python producer.py 3 pricelist.brakes.update "Обновление цен на колодки ---"
"""
import sys

import pika

from config import VARIANTS, names
from common import connect  # noqa: E402  (путь добавлен в config.py)


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else '1'
    routing_key = sys.argv[2] if len(sys.argv) > 2 else ''
    cfg = VARIANTS[variant]
    default_text = 'Импорт прайс-листа ' + cfg['sleep_char'] * 3
    text = ' '.join(sys.argv[3:]) or default_text
    exchange_name, _ = names(variant)

    connection = connect()
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange_name, exchange_type=cfg['exchange_type'],
                             durable=cfg['persistent'])

    properties = None
    if cfg['persistent']:
        properties = pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)

    channel.basic_publish(exchange=exchange_name, routing_key=routing_key,
                          body=text.encode(), properties=properties)
    print(f'SENT [{exchange_name}, key="{routing_key}"]: {text}')
    connection.close()


if __name__ == '__main__':
    main()
