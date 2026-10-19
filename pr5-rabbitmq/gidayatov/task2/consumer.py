"""ПР5, задание 2 — воркер (Гидаятов К.Г.: импорт прайс-листов).

Вариант 2: direct-обменник, символ сна '*'.
Запуск:  python consumer.py [ключ_привязки ...]   (можно запустить несколько экземпляров)
"""
import os
import sys
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 2: символ сна '*', обменник direct, сохранение при перезапуске: нет
SLEEP_CHAR = '*'
EXCHANGE_TYPE = 'direct'
PERSISTENT = False
EXCHANGE = PREFIX + '_tasks'
QUEUE = PREFIX + '_tasks_queue'
DEFAULT_BINDINGS = ['pricelist.import']


def process_message(channel, method, properties, body: bytes) -> None:
    text = body.decode()
    print(f'RECEIVED [{method.routing_key}]: {text}')
    sleep(text.count(SLEEP_CHAR))  # имитация ресурсоёмкой задачи
    print('INFO: Done')
    channel.basic_ack(delivery_tag=method.delivery_tag)  # ручное подтверждение


def main() -> None:
    bindings = sys.argv[1:] or DEFAULT_BINDINGS
    connection = connect()
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=PERSISTENT)
    # Одна именованная очередь на всех воркеров -> задачи делятся между ними
    channel.queue_declare(queue=QUEUE, durable=PERSISTENT)
    for key in bindings:
        channel.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=key)
    channel.basic_qos(prefetch_count=1)  # не больше одной неподтверждённой задачи на воркера
    channel.basic_consume(queue=QUEUE, on_message_callback=process_message)
    print(f'{EXCHANGE_TYPE} exchange {EXCHANGE}, bindings {bindings}. Waiting for tasks...')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
