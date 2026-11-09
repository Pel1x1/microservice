"""ПР10: проверка наблюдаемости (после `docker compose up` и `python tools/e2e_check.py`).

    python tools/observability_check.py

Проверяет, что метрики, логи и трассы действительно собираются:
- Prometheus опрашивает все восемь сервисов и RabbitMQ, есть метрики RED и бизнес-метрики;
- в Jaeger есть трасса создания заказа, проходящая через несколько сервисов и RabbitMQ;
- в Loki есть JSON-логи всех сервисов, и по trace_id из трассы находятся логи этого запроса.
Адреса можно переопределить: PROMETHEUS_URL, JAEGER_URL, LOKI_URL. Только стандартная библиотека.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

PROMETHEUS = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
JAEGER = os.getenv('JAEGER_URL', 'http://localhost:16686')
LOKI = os.getenv('LOKI_URL', 'http://localhost:3100')
SERVICES = ['user-service', 'store-service', 'catalog-service', 'inventory-service',
            'order-service', 'payment-service', 'delivery-service', 'review-service']
failed = []


def get(base: str, path: str, **params) -> dict:
    url = f'{base}{path}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


def check(name: str, ok: bool, detail: str = '') -> None:
    print(f'[{"OK" if ok else "FAIL"}] {name} {detail}')
    if not ok:
        failed.append(name)


def retry(fn, ready=bool, timeout: float = 60.0):
    """Метрики, трассы и логи доставляются с задержкой (scrape, batch, push), поэтому ждём,
    пока результат не станет полным (ready), но не дольше timeout."""
    deadline = time.time() + timeout
    while True:
        try:
            result = fn()
            if ready(result) or time.time() > deadline:
                return result
        except Exception:
            if time.time() > deadline:
                raise
        time.sleep(2)


def prom(query: str) -> list:
    return get(PROMETHEUS, '/api/v1/query', query=query)['data']['result']


def check_metrics() -> None:
    print('--- метрики (Prometheus)')
    targets = retry(lambda: [t for t in get(PROMETHEUS, '/api/v1/targets')['data']['activeTargets']
                             if t['health'] == 'up'], ready=lambda r: len(r) >= 9)
    up = {t['labels'].get('service', t['labels']['job']) for t in targets}
    check('все восемь сервисов опрашиваются', set(SERVICES) <= up, f'(up: {len(up & set(SERVICES))}/8)')
    check('метрики RabbitMQ опрашиваются', 'rabbitmq' in up)
    rate = retry(lambda: prom('sum by (service) (http_requests_total{job="automarket"})'),
                 ready=lambda r: len(r) == 8)
    check('Rate: http_requests_total по сервисам', len(rate) == 8, f'({len(rate)} сервисов)')
    errors = prom('sum(http_requests_total{job="automarket", status="4xx"})')
    check('Errors: ответы 4xx учтены', bool(errors) and float(errors[0]['value'][1]) > 0)
    p95 = prom('histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="automarket"}[5m])))')
    check('Duration: гистограмма времени ответа', bool(p95), f'(p95 = {float(p95[0]["value"][1]) * 1000:.1f} мс)' if p95 else '')
    events = retry(lambda: prom('sum by (routing_key) (automarket_events_published_total)'),
                   ready=lambda r: any(e['metric']['routing_key'] == 'order.created' for e in r))
    check('бизнес-метрика: опубликованные события', any(e['metric']['routing_key'] == 'order.created' for e in events),
          f'({len(events)} типов событий)')
    consumed = prom('sum(automarket_events_consumed_total{result="ok"})')
    check('бизнес-метрика: обработанные события', bool(consumed) and float(consumed[0]['value'][1]) > 0)
    rules = get(PROMETHEUS, '/api/v1/rules')['data']['groups']
    check('правила оповещений загружены', sum(len(g['rules']) for g in rules) >= 5)


def check_traces() -> str | None:
    print('--- трассировка (Jaeger)')
    services = set(retry(lambda: get(JAEGER, '/api/services')['data'],
                         ready=lambda r: set(SERVICES) <= set(r or [])) or [])
    check('все восемь сервисов отправляют трассы', set(SERVICES) <= services, f'({len(services & set(SERVICES))}/8)')
    traces = retry(lambda: get(JAEGER, '/api/traces', service='order-service',
                               operation='POST /api/orders', limit=20, lookback='1h')['data'])
    best = None
    for trace in traces or []:
        names = {trace['processes'][s['processID']]['serviceName'] for s in trace['spans']}
        if best is None or len(names) > len(best[1]):
            best = (trace, names)
    if best is None:
        check('трасса создания заказа', False)
        return None
    trace, names = best
    operations = {s['operationName'] for s in trace['spans']}
    check('трасса создания заказа проходит через несколько сервисов',
          {'order-service', 'inventory-service', 'payment-service'} <= names, f'({", ".join(sorted(names))})')
    check('в трассе есть синхронный REST-вызов', 'GET /api/stocks/{part_id}' in operations)
    check('в трассе есть публикация и получение через RabbitMQ',
          any(o.endswith(' send') for o in operations) and any(o.endswith(' receive') for o in operations))
    check('в трассе есть запросы к PostgreSQL', any(o.startswith(('INSERT', 'SELECT')) for o in operations),
          f'(всего span\'ов: {len(trace["spans"])})')
    return trace['traceID']


def check_logs(trace_id: str | None) -> None:
    print('--- логи (Loki)')
    labels = set(retry(lambda: get(LOKI, '/loki/api/v1/label/service/values')['data'],
                       ready=lambda r: set(SERVICES) <= set(r or [])) or [])
    check('логи всех восьми сервисов доставлены в Loki', set(SERVICES) <= labels, f'({len(labels & set(SERVICES))}/8)')
    end = time.time_ns()
    start = end - 3600 * 10 ** 9
    streams = get(LOKI, '/loki/api/v1/query_range', query='{service="order-service"}', limit=1,
                  start=start, end=end)['data']['result']
    line = streams[0]['values'][0][1] if streams else '{}'
    entry = json.loads(line)
    check('логи структурированы (JSON)', {'timestamp', 'level', 'service', 'message'} <= entry.keys())
    warnings = get(LOKI, '/loki/api/v1/query_range', query='{level="WARNING"}', limit=5,
                   start=start, end=end)['data']['result']
    check('уровень лога вынесен в метку (найдены WARNING: 4xx)', bool(warnings))
    if trace_id:
        related = retry(lambda: get(LOKI, '/loki/api/v1/query_range', query=f'{{service=~".+"}} |= "{trace_id}"',
                                    limit=50, start=start, end=end)['data']['result'],
                        ready=lambda r: len({s['stream']['service'] for s in r}) >= 2)
        services = {s['stream']['service'] for s in related or []}
        check('по trace_id находятся логи запроса во всех его сервисах', len(services) >= 2,
              f'({", ".join(sorted(services))})')


def main() -> None:
    check_metrics()
    check_logs(check_traces())
    print()
    if failed:
        print(f'НЕ ПРОЙДЕНО: {len(failed)}')
        sys.exit(1)
    print('НАБЛЮДАЕМОСТЬ РАБОТАЕТ: метрики, трассы и логи собираются')


if __name__ == '__main__':
    main()
