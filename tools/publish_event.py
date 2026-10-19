"""Эмуляция событий от сервисов, которые ещё не реализованы (payment, delivery).

python tools/publish_event.py payment.confirmed <order_id>
python tools/publish_event.py delivery.delivered <order_id>
"""
import sys
import json

import pika

AMQP_URL = 'amqp://guest:guest@localhost:5672/'
EXCHANGE = 'automarket'

routing_key, order_id = sys.argv[1], sys.argv[2]
connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE, exchange_type='topic', durable=True)
channel.basic_publish(exchange=EXCHANGE, routing_key=routing_key,
                      body=json.dumps({'order_id': order_id}).encode())
print(f'SENT {routing_key}: {order_id}')
connection.close()
