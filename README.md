# Маркетплейс автозапчастей — ПР5–8 «Микросервисная архитектура»

ИКБО-65-23: Начинкин И.С., Гидаятов К.Г., Киселев К.С., Сошнин Н.А.

| Папка | Работа |
|---|---|
| `pr5-rabbitmq/` | ПР5: RabbitMQ, задания 1 и 2: отдельное решение на каждого участника |
| `user-service/`, `store-service/`, `catalog-service/`, `inventory-service/`, `order-service/`, `payment-service/`, `delivery-service/`, `review-service/` | ПР7: восемь микросервисов из ПР4 (FastAPI, PostgreSQL, RabbitMQ) |
| `docker-compose.yaml` | ПР7: запуск всей системы одной командой |
| `*/tests/` + `.github/workflows/ci-cd.yml` | ПР8: unit- и интеграционные тесты, CI/CD |

## ПР5
У каждого участника своё решение в `pr5-rabbitmq/<фамилия>/` (подробности и таблица вариантов —
в `pr5-rabbitmq/README.md`).
```bash
cd pr5-rabbitmq && pip install -r requirements.txt
cd kiselev                              # или nachinkin / gidayatov / soshnin
python task1/consumer.py                # терминал 1
python task1/producer.py                # терминал 2
python task2/consumer.py                # воркер, можно запустить несколько
python task2/producer.py review.seller.recalc "Пересчёт рейтинга продавца 42 ---"
```
По умолчанию используется учебный сервер 51.250.26.59 (guest/guest123).
Для локального брокера: `RABBIT_HOST=localhost RABBIT_PASSWORD=guest`.

## ПР7: запуск системы
Восемь микросервисов из ПР4 (у каждого своя PostgreSQL, общий брокер RabbitMQ):
```bash
docker compose up --build
```
| Сервис | Порт | Swagger | Связи |
|---|---|---|---|
| user-service | 8003 | http://localhost:8003/docs | события `user.*` |
| store-service | 8004 | http://localhost:8004/docs | события `store.*` |
| catalog-service | 8005 | http://localhost:8005/docs | Sync REST → store-service; подписка `store.blocked` |
| inventory-service | 8001 | http://localhost:8001/docs | подписка `order.created`, `order.canceled` |
| order-service | 8002 | http://localhost:8002/docs | Sync REST → inventory-service; события заказа |
| payment-service | 8006 | http://localhost:8006/docs | подписка `order.created`, `order.canceled`; `payment.*` |
| delivery-service | 8007 | http://localhost:8007/docs | подписка `order.assembled`; `delivery.*` |
| review-service | 8008 | http://localhost:8008/docs | Sync REST → order-service |

RabbitMQ: http://localhost:15672 (guest/guest).

Сквозная проверка всей цепочки (регистрация → магазин → верификация → каталог → остаток → заказ →
оплата → сборка → доставка → отзыв, отмена оплаченного заказа, блокировка магазина):
```bash
python tools/e2e_check.py
```
Вручную, ключевые шаги (payment и delivery выполняют внешние системы — эквайринг и служба доставки,
их ответы эмулируются командами сервисов):
```bash
# остаток -> заказ -> резерв
curl -X PUT localhost:8001/api/stocks/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H 'Content-Type: application/json' \
  -d '{"store_id":"9b2f1c4e-1111-4a2a-8201-537cdff25fed","price":"2500.00","quantity":10}'
curl -X POST localhost:8002/api/orders -H 'Content-Type: application/json' \
  -d '{"customer_id":"85db966c-67f1-411e-95c0-f02edfa5464a","address":"Москва, пр. Вернадского, 78",
       "items":[{"part_id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","quantity":2}]}'
# payment-service сам создал оплату по order.created; эквайринг подтверждает её:
curl "localhost:8006/api/payments?order_id=<order_id>"
curl -X POST "localhost:8006/api/payments/<payment_id>:confirm"      # -> заказ confirmed
curl -X POST "localhost:8002/api/orders/<order_id>:assemble"         # -> delivery-service назначил доставку
curl "localhost:8007/api/deliveries?order_id=<order_id>"
curl -X POST "localhost:8007/api/deliveries/<delivery_id>:ship"
curl -X POST "localhost:8007/api/deliveries/<delivery_id>:deliver"   # -> заказ completed
```
(`tools/publish_event.py` по-прежнему умеет публиковать любое событие вручную, если нужно проверить сервис отдельно.)

## ПР8: тесты локально
```bash
cd order-service           # или любой из восьми сервисов
pip install -r requirements-dev.txt
pytest tests/unit
docker run -d --name pg-tests -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16
pytest tests/integration
```
В GitHub Actions тесты запускаются автоматически при каждом push; образы публикуются в GHCR
только если все тесты прошли.
