# Маркетплейс автозапчастей — ПР5–8 «Микросервисная архитектура»

ИКБО-65-23: Начинкин И.С., Гидаятов К.Г., Киселев К.С., Сошнин Н.А.

| Папка | Работа |
|---|---|
| `pr5-rabbitmq/` | ПР5: RabbitMQ, задания 1 и 2 (все три варианта, выбор аргументом) |
| `inventory-service/` | ПР7: сервис остатков (PostgreSQL, RabbitMQ) |
| `order-service/` | ПР7: сервис заказов (PostgreSQL, RabbitMQ, REST-вызов inventory-service) |
| `docker-compose.yaml` | ПР7: запуск всей системы одной командой |
| `*/tests/` + `.github/workflows/ci-cd.yml` | ПР8: unit- и интеграционные тесты, CI/CD |

## ПР5
```bash
cd pr5-rabbitmq && pip install -r requirements.txt
# Задание 1 (вариант 1|2|3)
python task1/consumer.py 2
python task1/producer.py 2 "Заказ создан"
# Задание 2 (вариант 1|2|3), можно запустить несколько consumer
cd task2
python consumer.py 3
python producer.py 3 pricelist.brakes.update "Обновление цен ----"
```
По умолчанию используется учебный сервер 51.250.26.59 (guest/guest123).
Для локального брокера: `RABBIT_HOST=localhost RABBIT_PASSWORD=guest`.

## ПР7: запуск системы
```bash
docker compose up --build
```
- inventory-service: http://localhost:8001/docs
- order-service: http://localhost:8002/docs
- RabbitMQ: http://localhost:15672 (guest/guest)

Сценарий проверки:
```bash
# 1. Продавец заводит остаток
curl -X PUT localhost:8001/api/stocks/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H 'Content-Type: application/json' \
  -d '{"store_id":"9b2f1c4e-1111-4a2a-8201-537cdff25fed","price":"2500.00","quantity":10}'
# 2. Покупатель оформляет заказ -> order.created -> резерв в inventory-service
curl -X POST localhost:8002/api/orders -H 'Content-Type: application/json' \
  -d '{"customer_id":"85db966c-67f1-411e-95c0-f02edfa5464a","address":"Москва, пр. Вернадского, 78",
       "items":[{"part_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","quantity":2}]}'
curl localhost:8001/api/stocks/3fa85f64-5717-4562-b3fc-2c963f66afa6   # reserved = 2
# 3. Эмуляция оплаты и доставки (payment/delivery-service ещё не реализованы)
pip install pika
python tools/publish_event.py payment.confirmed <order_id>
curl -X POST localhost:8002/api/orders/<order_id>:assemble
python tools/publish_event.py delivery.delivered <order_id>
curl localhost:8002/api/orders/<order_id>                            # status = completed
```

## ПР8: тесты локально
```bash
cd order-service           # или inventory-service
pip install -r requirements-dev.txt
pytest tests/unit
docker run -d --name pg-tests -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16
pytest tests/integration
```
В GitHub Actions тесты запускаются автоматически при каждом push; образы публикуются в GHCR
только если все тесты прошли.
