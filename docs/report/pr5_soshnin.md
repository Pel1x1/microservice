# ПР5. RabbitMQ — Сошнин Н.А.

## Цель работы

Освоить базовые схемы обмена сообщениями в RabbitMQ: простейшую схему «поставщик → очередь →
потребитель» и схему взаимодействия с нагрузкой (несколько воркеров). Предметная область —
маркетплейс автозапчастей, тема работы: передача посылок в службу доставки.

Номер варианта: **1** (Сошнин Н.А.). Имена очередей и обменников начинаются с `ikbo-65-23_soshnin`,
чтобы работы четырёх участников команды не пересекались на общем сервере.

## Задание 1. Простейшая схема

### Вариант и параметры

| Параметр | Значение |
|---|---|
| Вариант | 1 |
| Тип очереди | эксклюзивная очередь |
| Параметр pika | `exclusive=True` |
| Имя очереди | `ikbo-65-23_soshnin` |
| Особенность | очередь объявляет потребитель; поставщик её не объявляет, а публикует через обменник по умолчанию (иначе `RESOURCE_LOCKED`) |

### Листинг поставщика (`soshnin/task1/producer.py`)

```python
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
```

### Листинг потребителя (`soshnin/task1/consumer.py`)

```python
"""ПР5, задание 1 — потребитель (Сошнин Н.А., тема: передача посылок в доставку).

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
```

### Проверка

Запуск: `RABBIT_HOST=localhost RABBIT_PASSWORD=guest python soshnin/task1/consumer.py`, затем
`python soshnin/task1/producer.py` (три раза). Полный вывод консоли — `pr5-rabbitmq/soshnin/run_log.txt`.

- ✔ t1: потребитель получил 3 из 3 
- ✔ t1: эксклюзивная очередь исчезла после закрытия соединения 

Рисунок 5.1 — Консоль потребителя и поставщика: отправлено 3 сообщения, получено 3 (вставить скриншот)

Рисунок 5.2 — Вкладка Queues веб-интерфейса RabbitMQ: параметры очереди `ikbo-65-23_soshnin` (вставить скриншот)

## Задание 2. Схема с нагрузкой

### Вариант и параметры

| Параметр | Значение |
|---|---|
| Вариант | 1 |
| Символ сна | `#` (1 символ = 1 секунда обработки) |
| Тип обменника | fanout |
| Сохранение при перезапуске RabbitMQ | да (durable-обменник, durable-очередь, persistent-сообщения) |
| Обменник | `ikbo-65-23_soshnin_tasks` |
| Очередь | `ikbo-65-23_soshnin_tasks_queue` |
| Ключ маршрутизации | — |
| Подтверждение / prefetch | ручной `basic_ack`, `basic_qos(prefetch_count=1)` |

### Листинг поставщика (`soshnin/task2/producer.py`)

```python
"""ПР5, задание 2 — поставщик задач (Сошнин Н.А.: передача партий посылок в службу доставки).

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
DEFAULT_TEXT = 'Передача партии посылок 12 в службу доставки ##'


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
```

### Листинг воркера (`soshnin/task2/consumer.py`)

```python
"""ПР5, задание 2 — воркер (Сошнин Н.А.: передача партий посылок в службу доставки).

Вариант 1: fanout-обменник, символ сна '#'.
Запуск:  python consumer.py [ключ_привязки ...]   (можно запустить несколько экземпляров)
"""
import os
import sys
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, PREFIX  # noqa: E402

# Вариант 1: символ сна '#', обменник fanout, сохранение при перезапуске: да
SLEEP_CHAR = '#'
EXCHANGE_TYPE = 'fanout'
PERSISTENT = True
EXCHANGE = PREFIX + '_tasks'
QUEUE = PREFIX + '_tasks_queue'
DEFAULT_BINDINGS = ['']


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
```

### Проверка

Запущены два воркера на одной именованной очереди; отправлена одна долгая задача (5 символов сна)
и три коротких (по 1 символу). Из-за `prefetch_count=1` долгую задачу берёт один воркер, а три
коротких достаются свободному.

- ✔ t2: все 4 задачи обработаны (1+3)
- ✔ t2: долгую берёт один воркер, короткие достаются свободному (долгая: 1, остальные: 3)
- ✔ t2: после перезапуска очередь, обменник и 2 сообщения на месте 
- ✔ t2: воркер получил 2 сообщения после перезапуска 

Рисунок 5.3 — Консоли двух воркеров: долгая задача у одного, три короткие у другого (вставить скриншот)

Рисунок 5.4 — Вкладка Exchanges: обменник `ikbo-65-23_soshnin_tasks`, тип fanout, признак Durable (вставить скриншот)

Рисунок 5.5 — Вкладка Queues после перезапуска брокера: очередь и сообщения на месте (вставить скриншот)

## Вывод

В работе реализованы обе схемы RabbitMQ для варианта 1: эксклюзивная очередь в задании 1 и fanout-обменник
с сохранением сообщений при перезапуске брокера в задании 2.
Проверка на локальном брокере: 6/6 проверок пройдено.

## Какие скриншоты нужно снять

1. Рис. 5.1 — консоли потребителя и поставщика (задание 1).
2. Рис. 5.2 — http://localhost:15672 (или сервер кафедры), Queues: колонки Features / параметры очереди задания 1.
3. Рис. 5.3 — два окна воркеров (задание 2), видно распределение долгой и коротких задач.
4. Рис. 5.4 — Exchanges: обменник задания 2, тип и Durable.
5. Рис. 5.5 — Queues после `docker restart rabbitmq` (для локальной проверки).
