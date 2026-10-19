"""Параметры вариантов ПР5, задание 2 (схема с нагрузкой).

Предметная задача: тяжёлая обработка прайс-листов продавцов маркетплейса
автозапчастей. Количество символов сна в сообщении = секунды обработки.
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import QUEUE_PREFIX  # noqa: E402,F401

VARIANTS = {
    # символ сна, тип обменника, сохранять ли сообщения при перезапуске RabbitMQ
    '1': {'sleep_char': '#', 'exchange_type': 'fanout', 'persistent': True},
    '2': {'sleep_char': '*', 'exchange_type': 'direct', 'persistent': False},
    '3': {'sleep_char': '-', 'exchange_type': 'topic', 'persistent': True},
}

# Ключи привязки очереди к обменнику по умолчанию (для fanout игнорируются)
DEFAULT_BINDINGS = {
    'fanout': [''],
    'direct': ['pricelist.import'],
    'topic': ['pricelist.#'],
}


def names(variant: str) -> tuple[str, str]:
    exchange = f'{QUEUE_PREFIX}_tasks_v{variant}'
    queue = f'{QUEUE_PREFIX}_tasks_v{variant}_queue'
    return exchange, queue
