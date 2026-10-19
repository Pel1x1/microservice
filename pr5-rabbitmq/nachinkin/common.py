"""Подключение к RabbitMQ (nachinkin).

Параметры берутся из переменных окружения; по умолчанию — учебный сервер кафедры.
Локально:  RABBIT_HOST=localhost RABBIT_PASSWORD=guest
"""
import os

import pika

RABBIT_HOST = os.getenv('RABBIT_HOST', '51.250.26.59')
RABBIT_PORT = int(os.getenv('RABBIT_PORT', '5672'))
RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest123')

# Имена очередей и обменников: ikbo-65-23_<фамилия>...
PREFIX = 'ikbo-65-23_nachinkin'


def connect() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(RABBIT_HOST, RABBIT_PORT, credentials=credentials)
    return pika.BlockingConnection(parameters)
