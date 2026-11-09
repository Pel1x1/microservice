"""ПР10: наблюдаемость сервиса — метрики, структурированные логи и трассировка.

Модуль одинаковый во всех восьми сервисах (у каждого сервиса свой Docker-контекст,
поэтому общий пакет не используется).

- Метрики: /metrics в формате Prometheus (RED: интенсивность, ошибки, длительность)
  и бизнес-счётчики событий RabbitMQ.
- Логи: JSON в stdout, в каждой записи trace_id — по нему из Grafana (Loki) можно
  перейти к трассе в Jaeger.
- Трассировка: OpenTelemetry SDK, экспорт в Jaeger по OTLP/HTTP. Включается, только
  если задана переменная OTEL_EXPORTER_OTLP_ENDPOINT (в тестах она не задана).
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from importlib.util import find_spec

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.engine import Engine
from opentelemetry import trace

logger = logging.getLogger('automarket')

# Бизнес-метрики: сколько событий опубликовано и обработано (по ключу маршрутизации)
EVENTS_PUBLISHED = Counter(
    'automarket_events_published_total', 'Опубликованные доменные события', ['routing_key'])
EVENTS_CONSUMED = Counter(
    'automarket_events_consumed_total', 'Обработанные события из RabbitMQ', ['routing_key', 'result'])

# Поля, которые можно передать в лог через extra={...}
_EXTRA_FIELDS = ('method', 'path', 'status', 'duration_ms', 'routing_key', 'client')


class JsonFormatter(logging.Formatter):
    """Структурированный лог: одна JSON-строка на событие."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec='milliseconds'),
            'level': record.levelname,
            'service': self.service,
            'logger': record.name,
            'message': record.getMessage(),
        }
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            entry['trace_id'] = format(span_context.trace_id, '032x')
            entry['span_id'] = format(span_context.span_id, '016x')
        for key in _EXTRA_FIELDS:
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging(service: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    # логи uvicorn тоже в JSON; access-лог заменён собственным (см. _access_log)
    for name in ('uvicorn', 'uvicorn.error'):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    logging.getLogger('uvicorn.access').disabled = True
    for noisy in ('pika', 'aio_pika', 'aiormq'):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def setup_tracing(service: str, engine: Engine) -> bool:
    endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
    if not endpoint:
        return False
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    provider = TracerProvider(resource=Resource.create({
        'service.name': service,
        'service.namespace': 'automarket',
        'deployment.environment': os.getenv('ENVIRONMENT', 'local'),
    }))
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=f'{endpoint.rstrip("/")}/v1/traces')))
    trace.set_tracer_provider(provider)

    SQLAlchemyInstrumentor().instrument(engine=engine)  # запросы к PostgreSQL
    # остальные библиотеки инструментируются, только если сервис их использует
    if find_spec('requests'):
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()             # Sync REST: передаёт traceparent соседям
    if find_spec('pika'):
        from opentelemetry.instrumentation.pika import PikaInstrumentor
        PikaInstrumentor().instrument()                 # публикация: контекст в заголовки сообщения
    if find_spec('aio_pika'):
        from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
        AioPikaInstrumentor().instrument()              # потребление: продолжение той же трассы
    return True


def setup_observability(app: FastAPI, service: str, engine: Engine) -> None:
    setup_logging(service)
    tracing = setup_tracing(service, engine)

    @app.middleware('http')
    async def _access_log(request: Request, call_next) -> Response:
        if request.url.path in ('/metrics', '/health'):
            return await call_next(request)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
            logger.log(level, f'{request.method} {request.url.path} -> {status}', extra={
                'method': request.method, 'path': request.url.path, 'status': status,
                'duration_ms': round((time.perf_counter() - start) * 1000, 1),
                'client': request.client.host if request.client else None,
            })

    @app.get('/health', include_in_schema=False)
    def health() -> JSONResponse:
        """Проверка живости для docker compose, CI и Serverless Containers."""
        try:
            with engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return JSONResponse({'status': 'ok', 'service': service})
        except Exception as e:
            return JSONResponse({'status': 'error', 'service': service, 'detail': str(e)}, status_code=503)

    if tracing:
        # подключается последним, чтобы span запроса охватывал access-лог (trace_id в логе)
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, excluded_urls='metrics,health',
                                           exclude_spans=['receive', 'send'])  # без служебных ASGI-span'ов

    # бакеты гистограммы времени ответа: сервисы отвечают за миллисекунды, а бакеты
    # по умолчанию (0.1, 0.5, 1 с) не позволяют посчитать перцентили точнее 100 мс
    Instrumentator(excluded_handlers=['/metrics', '/health']).instrument(
        app, latency_lowr_buckets=(0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
    ).expose(app, include_in_schema=False)
    logger.info(f'{service}: observability ready (tracing={"on" if tracing else "off"})')
