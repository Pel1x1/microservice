# /tests/unit/test_observability.py — ПР10: формат логов, /health и /metrics
import json
import logging
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.observability import JsonFormatter, EVENTS_PUBLISHED, setup_observability


def make_record(message: str, **extra) -> logging.LogRecord:
    record = logging.LogRecord('automarket', logging.WARNING, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_log_is_single_json_line():
    line = JsonFormatter('test-service').format(make_record('POST /api/x -> 409', status=409, path='/api/x'))
    entry = json.loads(line)
    assert '\n' not in line
    assert entry['level'] == 'WARNING'
    assert entry['service'] == 'test-service'
    assert entry['message'] == 'POST /api/x -> 409'
    assert entry['status'] == 409 and entry['path'] == '/api/x'
    assert entry['timestamp'].endswith('+00:00')
    assert 'trace_id' not in entry  # вне трассы идентификатора нет


def test_log_contains_exception():
    try:
        raise RuntimeError('db is down')
    except RuntimeError:
        record = make_record('failed')
        record.exc_info = sys.exc_info()
    entry = json.loads(JsonFormatter('s').format(record))
    assert 'RuntimeError: db is down' in entry['exception']


@pytest.fixture(scope='module')
def client() -> TestClient:
    # одно приложение на модуль: метрики регистрируются в общем реестре Prometheus один раз
    app = FastAPI()
    setup_observability(app, 'test-service', create_engine('sqlite://'))

    @app.get('/api/ping')
    def ping():
        return {'pong': True}

    return TestClient(app)


def test_health_checks_database(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'test-service'}


def test_metrics_count_requests(client):
    assert client.get('/api/ping').status_code == 200
    body = client.get('/metrics').text
    assert 'http_requests_total{handler="/api/ping",method="GET",status="2xx"}' in body
    assert 'http_request_duration_seconds_bucket' in body
    assert 'handler="/metrics"' not in body  # служебные запросы не учитываются


def test_events_counter():
    before = EVENTS_PUBLISHED.labels('test.happened')._value.get()
    EVENTS_PUBLISHED.labels('test.happened').inc()
    assert EVENTS_PUBLISHED.labels('test.happened')._value.get() == before + 1
