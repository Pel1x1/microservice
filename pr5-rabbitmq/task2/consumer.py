"""ПР5, задание 2 — потребитель (воркер). Можно запускать несколько экземпляров.

Запуск:  python consumer.py <вариант> [ключ_привязки ...]
"""
import sys
from time import sleep

from config import VARIANTS, DEFAULT_BINDINGS, names
from common import connect  # noqa: E402  (путь добавлен в config.py)


def make_handler(sleep_char: str):
    def process_message(channel, method, properties, body: bytes) -> None:
        text = body.decode()
        print(f'RECEIVED [{method.routing_key}]: {text}')
        sleep(text.count(sleep_char))       # имитация ресурсоёмкой задачи
        print('INFO: Done')
        channel.basic_ack(delivery_tag=method.delivery_tag)  # ручное подтверждение
    return process_message


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else '1'
    cfg = VARIANTS[variant]
    bindings = sys.argv[2:] or DEFAULT_BINDINGS[cfg['exchange_type']]
    exchange_name, queue_name = names(variant)

    connection = connect()
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange_name, exchange_type=cfg['exchange_type'],
                             durable=cfg['persistent'])
    # Именованная очередь общая для всех воркеров -> задачи распределяются между ними.
    channel.queue_declare(queue=queue_name, durable=cfg['persistent'])
    for key in bindings:
        channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=key)

    channel.basic_qos(prefetch_count=1)     # не более одной неподтверждённой задачи на воркер
    channel.basic_consume(queue=queue_name, on_message_callback=make_handler(cfg['sleep_char']))

    print(f'Variant {variant}: {cfg["exchange_type"]} exchange {exchange_name}, '
          f'bindings {bindings}. Waiting for tasks...')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
