"""Общие настройки подключения к RabbitMQ для заданий ПР5.

По умолчанию используется учебный сервер кафедры. Для локального запуска:
    docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
    set RABBIT_HOST=localhost, RABBIT_USER=guest, RABBIT_PASSWORD=guest
"""
import os

import pika

RABBIT_HOST = os.getenv('RABBIT_HOST', '51.250.26.59')
RABBIT_PORT = int(os.getenv('RABBIT_PORT', '5672'))
RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest123')

# Формат имени очереди по заданию: <группа>_<фамилия>
QUEUE_PREFIX = os.getenv('QUEUE_PREFIX', 'ikbo-65-23_nachinkin')


def connect() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    params = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, credentials=credentials)
    return pika.BlockingConnection(params)
