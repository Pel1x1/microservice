# Список изменений (для переноса в отчёт ПР5–8)

Дата проверки: 2026-10-19. Python 3.12 (как в Dockerfile и CI), Docker 29.2, `postgres:16`, `rabbitmq:3-management`.

## 1. Что изменено в файлах

| Файл | Что изменено | Почему |
|---|---|---|
| `.github/workflows/ci-cd.yml` | **Создан.** Job `test`: матрица по двум сервисам, service-контейнер `postgres:16`, `pytest tests/unit`, затем `pytest tests/integration`. Job `build-and-push`: `needs: test`, только на push, публикация образов в GHCR через `GITHUB_TOKEN`, владелец приводится к нижнему регистру | README и ТЗ ссылались на файл, которого не было |
| `.gitignore` | Создан: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, `.DS_Store` | В проекте файла не было; не коммитить окружение и секреты |
| `pr5-rabbitmq/{common.py,task1/*,task2/*}` | **Удалены** общий код и выбор варианта аргументом (остались в git, коммит `e61ce07`) | Нужно 4 самостоятельных решения |
| `pr5-rabbitmq/<фамилия>/{common.py,task1/{producer,consumer}.py,task2/{producer,consumer}.py}` | **Созданы** для nachinkin, gidayatov, kiselev, soshnin. Параметры варианта зашиты константами; свои имена очередей и обменников `ikbo-65-23_<фамилия>…`; своя предметная тема и routing key; путь к `common.py` строится от `__file__` | Раздел 3 ТЗ |
| `pr5-rabbitmq/<фамилия>/run_log.txt` | Созданы: вывод реальной проверки на локальном RabbitMQ, включая `docker restart` брокера | Раздел 3.3 ТЗ |
| `pr5-rabbitmq/README.md` | Создан: таблица «кто — какой вариант», запуск | Раздел 3.2 ТЗ |
| `README.md` | Раздел ПР5 переписан под новую структуру | Старые команды (`python task1/consumer.py 2`) больше не работают |
| `docs/report/pr5_<фамилия>.md` (4 шт.) | Созданы заготовки разделов отчёта по ПР5 с листингами и списком скриншотов | Раздел 3.4 ТЗ |
| `docs/CHANGES.md` | Этот файл | Раздел 8 ТЗ |

**Код сервисов (`order-service`, `inventory-service`), тесты, Dockerfile, `docker-compose.yaml`, `requirements*.txt`
и `tools/publish_event.py` исправлений не потребовали**: все 65 тестов и сценарий README прошли с первого запуска.
Версии библиотек из `requirements.txt` ставятся на Python 3.12 без изменений.

### Варианты ПР5

Номера билетов не предоставлены, поэтому варианты розданы по порядку, чтобы были выполнены все три
(по решению пользователя). Задания 1 и 2 у каждого — по одному варианту.

| Участник | Вариант | Тема |
|---|---|---|
| Начинкин И.С. | 1 | заказы |
| Гидаятов К.Г. | 2 | прайс-листы |
| Киселев К.С. | 3 | рейтинг по отзывам |
| Сошнин Н.А. | 1 | передача посылок (вариант совпал с Начинкиным, код и данные другие) |

Если вариант нужно привязать к билетам, поменяйте константы «Вариант N» и параметры в файлах решения.

## 2. Что перенести в отчёт

**ПР6 (API).** Без изменений. Все пути, методы и коды ответов совпадают с реализацией
(проверено: 201/400/503 для `POST /api/orders`; 404/409 для `:assemble` и `:cancel`; 422 при некорректном UUID).

**ПР7.**
- Маршруты с двоеточием `/{order_id}:assemble` и `/{order_id}:cancel` работают в FastAPI 0.115.6 / Starlette без изменений.
- `cancel` работает и без тела, и с `{"reason": "..."}`.
- Запуск: `docker compose up --build`; сценарий остаток → заказ → резерв → `payment.confirmed` → assemble → `delivery.delivered` → `completed` пройден.
- Резерв снимается при отмене (`reserved` уменьшается), при остановленном inventory-service `POST /api/orders` отдаёт 503.
- Замечание для текста отчёта: при ручной проверке в zsh ID заказа с двоеточием нужно писать как `"${ORDER_ID}:assemble"` (без фигурных скобок zsh портит URL).

**ПР8.**
- Число тестов не изменилось: 65 (order-service 7 + 16 unit, 7 интеграционных; inventory-service 8 + 18 unit, 9 интеграционных).
- Библиотеки: pytest 8.3.4, FastAPI 0.115.6, pydantic 2.10.4, SQLAlchemy 2.0.36, psycopg2-binary 2.9.10, aio-pika 9.5.4, pika 1.3.2.
- Состав CI описан в таблице выше; шаги CI дополнительно прогнаны в чистом контейнере `python:3.12`.

**ПР5.** Результаты проверки каждого участника — в `pr5-rabbitmq/<фамилия>/run_log.txt` (итог: nachinkin 6/6, gidayatov 7/7, kiselev 7/7, soshnin 6/6).

## 3. Итог `pytest`

| Сервис | Unit | Интеграционные |
|---|---|---|
| order-service | 23 passed | 7 passed |
| inventory-service | 26 passed | 9 passed |

Запуск: `pytest tests/unit`, затем `pytest tests/integration` (с `postgres:16`, пароль `password`, порт 5432); вместе — 30 и 35 тестов.

## 4. Репозиторий и CI

- Репозиторий: https://github.com/Pel1x1/microservice (приватный).
- Статус CI: **ещё не запускался** — push заблокирован отсутствием scope `workflow` у токена `gh`. Обновить после первого запуска.

## 5. Скриншоты для отчёта

**ПР5** — по каждому участнику (подробный список — в конце `docs/report/pr5_<фамилия>.md`):

| Рис. | Что снять |
|---|---|
| 5.1 | консоли потребителя и поставщика, задание 1 (3 отправлено, 3 получено) |
| 5.2 | веб-интерфейс RabbitMQ → Queues: параметры очереди задания 1 |
| 5.3 | два окна воркеров (задание 2): долгая задача у одного, короткие у другого |
| 5.4 | Exchanges: обменник задания 2, тип и Durable |
| 5.5 | Queues после `docker restart rabbitmq` |

**ПР7:**
- `docker compose up --build`: запущенные контейнеры (`docker compose ps`);
- Swagger inventory-service (http://localhost:8001/docs) и order-service (http://localhost:8002/docs);
- ответы `curl` по шагам сценария (остаток, заказ, резерв `reserved = 2`, статус `completed`);
- RabbitMQ Management (http://localhost:15672): очереди `ikbo-65-23_automarket_*`.

**ПР8:**
- вывод `pytest tests/unit -v` и `pytest tests/integration -v` для каждого сервиса;
- вкладка Actions на GitHub: зелёный запуск с обоими job (`test`, `build-and-push`);
- раздел Packages с опубликованными образами.
