"""Сквозная проверка всех восьми сервисов (после `docker compose up --build`).

    python tools/e2e_check.py

Идёт по цепочке из ПР4: регистрация → магазин → верификация → каталог → остаток →
заказ → оплата → сборка → доставка → отзыв, затем отмена оплаченного заказа и блокировка
магазина. Только стандартная библиотека. Код возврата 1, если какая-то проверка не прошла.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4

PORTS = {'inventory': 8001, 'order': 8002, 'user': 8003, 'store': 8004,
         'catalog': 8005, 'payment': 8006, 'delivery': 8007, 'review': 8008}
failed = []


def call(service: str, method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f'http://localhost:{PORTS[service]}/api{path}', data=data,
                                     method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or 'null')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or 'null')


def check(name: str, ok: bool, detail: str = '') -> None:
    print(f'[{"OK" if ok else "FAIL"}] {name} {detail}')
    if not ok:
        failed.append(name)


def expect(name: str, response, status: int):
    check(name, response[0] == status, f'(HTTP {response[0]}, ожидалось {status})')
    return response[1]


def wait_for(name: str, getter, predicate, timeout: float = 20.0):
    """События идут через RabbitMQ асинхронно, поэтому результат ждём."""
    deadline = time.time() + timeout
    value = None
    while time.time() < deadline:
        value = getter()
        if predicate(value):
            check(name, True)
            return value
        time.sleep(0.5)
    check(name, False, f'(последнее значение: {value})')
    return value


def main() -> None:
    suffix = uuid4().hex[:8]
    print('--- user-service')
    buyer = expect('регистрация покупателя', call('user', 'POST', '/users', {
        'email': f'buyer-{suffix}@example.com', 'name': 'Покупатель'}), 201)
    seller = expect('регистрация продавца', call('user', 'POST', '/users', {
        'email': f'seller-{suffix}@example.com', 'name': 'Продавец', 'role': 'seller'}), 201)
    expect('повторный email -> 409', call('user', 'POST', '/users', {
        'email': f'buyer-{suffix}@example.com', 'name': 'Дубль'}), 409)
    expect('регистрация администратора -> 409', call('user', 'POST', '/users', {
        'email': f'root-{suffix}@example.com', 'name': 'Root', 'role': 'admin'}), 409)

    print('--- store-service + catalog-service')
    store = expect('создание магазина', call('store', 'POST', '/stores', {
        'owner_id': seller['id'], 'name': f'АвтоМир {suffix}'}), 201)
    check('магазин ждёт верификации', store['status'] == 'pending')
    part_body = {'store_id': store['id'], 'name': f'Колодки {suffix}', 'category': 'Тормоза',
                 'brand': 'Brembo', 'compatible_cars': ['Toyota Camry 2018']}
    expect('публикация в неверифицированном магазине -> 409', call('catalog', 'POST', '/parts', part_body), 409)
    expect('верификация магазина', call('store', 'POST', f'/stores/{store["id"]}:verify'), 200)
    part = expect('публикация запчасти (catalog -> store, Sync REST)', call('catalog', 'POST', '/parts', part_body), 201)
    found = expect('поиск по автомобилю', call('catalog', 'GET', f'/parts?car=toyota%20camry%202018&store_id={store["id"]}'), 200)
    check('запчасть найдена в каталоге', [p['id'] for p in found] == [part['id']])

    print('--- inventory-service + order-service')
    expect('остаток запчасти', call('inventory', 'PUT', f'/stocks/{part["id"]}', {
        'store_id': store['id'], 'price': '2500.00', 'quantity': 10}), 200)
    order_body = {'customer_id': buyer['id'], 'address': 'Москва, пр. Вернадского, 78',
                  'items': [{'part_id': part['id'], 'quantity': 2}]}
    order = expect('оформление заказа (order -> inventory, Sync REST)', call('order', 'POST', '/orders', order_body), 201)
    check('сумма заказа', order['total'] == '5000.00', f'({order["total"]})')
    expect('заказ сверх остатка -> 400', call('order', 'POST', '/orders', {
        **order_body, 'items': [{'part_id': part['id'], 'quantity': 999}]}), 400)
    wait_for('резерв создан по событию order.created',
             lambda: call('inventory', 'GET', f'/stocks/{part["id"]}')[1]['reserved'], lambda r: r == 2)

    print('--- payment-service')
    payment = wait_for('оплата создана по событию order.created',
                       lambda: (call('payment', 'GET', f'/payments?order_id={order["id"]}')[1] or [None])[0],
                       lambda p: p is not None)
    check('оплата ждёт подтверждения', payment['status'] == 'pending' and payment['amount'] == '5000.00')
    expect('отзыв до доставки -> 409', call('review', 'POST', '/reviews', {
        'order_id': order['id'], 'part_id': part['id'], 'author_id': buyer['id'], 'rating': 5}), 409)
    expect('подтверждение оплаты (эквайринг)', call('payment', 'POST', f'/payments/{payment["id"]}:confirm'), 200)
    expect('повторное подтверждение -> 409', call('payment', 'POST', f'/payments/{payment["id"]}:confirm'), 409)
    wait_for('заказ confirmed по событию payment.confirmed',
             lambda: call('order', 'GET', f'/orders/{order["id"]}')[1]['status'], lambda s: s == 'confirmed')

    print('--- delivery-service')
    expect('сборка заказа', call('order', 'POST', f'/orders/{order["id"]}:assemble'), 200)
    delivery = wait_for('доставка назначена по событию order.assembled',
                        lambda: (call('delivery', 'GET', f'/deliveries?order_id={order["id"]}')[1] or [None])[0],
                        lambda d: d is not None)
    expect('доставка до передачи -> 409', call('delivery', 'POST', f'/deliveries/{delivery["id"]}:deliver'), 409)
    expect('передача в доставку', call('delivery', 'POST', f'/deliveries/{delivery["id"]}:ship'), 200)
    expect('подтверждение доставки', call('delivery', 'POST', f'/deliveries/{delivery["id"]}:deliver'), 200)
    wait_for('заказ completed по событию delivery.delivered',
             lambda: call('order', 'GET', f'/orders/{order["id"]}')[1]['status'], lambda s: s == 'completed')

    print('--- review-service')
    review = expect('отзыв на доставленный заказ (review -> order, Sync REST)', call('review', 'POST', '/reviews', {
        'order_id': order['id'], 'part_id': part['id'], 'author_id': buyer['id'], 'rating': 5,
        'text': 'Отличные колодки'}), 201)
    expect('повторный отзыв -> 409', call('review', 'POST', '/reviews', {
        'order_id': order['id'], 'part_id': part['id'], 'author_id': buyer['id'], 'rating': 1}), 409)
    expect('отзыв от чужого покупателя -> 409', call('review', 'POST', '/reviews', {
        'order_id': order['id'], 'part_id': part['id'], 'author_id': str(uuid4()), 'rating': 1}), 409)
    expect('получение отзыва', call('review', 'GET', f'/reviews/{review["id"]}'), 200)
    rating = expect('рейтинг запчасти', call('review', 'GET', f'/ratings/{part["id"]}'), 200)
    check('рейтинг = 5.0 по одному отзыву', rating['count'] == 1 and rating['average'] == 5.0)

    print('--- отмена оплаченного заказа (возврат и снятие резерва)')
    order2 = expect('второй заказ', call('order', 'POST', '/orders', {
        **order_body, 'items': [{'part_id': part['id'], 'quantity': 3}]}), 201)
    pay2 = wait_for('оплата второго заказа создана',
                    lambda: (call('payment', 'GET', f'/payments?order_id={order2["id"]}')[1] or [None])[0],
                    lambda p: p is not None)
    expect('подтверждение оплаты второго заказа', call('payment', 'POST', f'/payments/{pay2["id"]}:confirm'), 200)
    wait_for('второй заказ confirmed', lambda: call('order', 'GET', f'/orders/{order2["id"]}')[1]['status'],
             lambda s: s == 'confirmed')
    expect('отмена оплаченного заказа', call('order', 'POST', f'/orders/{order2["id"]}:cancel',
                                              {'reason': 'передумал'}), 200)
    wait_for('оплата refunded по событию order.canceled',
             lambda: call('payment', 'GET', f'/payments/{pay2["id"]}')[1]['status'], lambda s: s == 'refunded')
    wait_for('резерв снят (reserved = 2)',
             lambda: call('inventory', 'GET', f'/stocks/{part["id"]}')[1]['reserved'], lambda r: r == 2)

    print('--- блокировки')
    expect('блокировка магазина', call('store', 'POST', f'/stores/{store["id"]}:block'), 200)
    wait_for('запчасти магазина сняты с публикации по событию store.blocked',
             lambda: call('catalog', 'GET', f'/parts?store_id={store["id"]}')[1], lambda parts: parts == [])
    expect('блокировка пользователя', call('user', 'POST', f'/users/{buyer["id"]}:block'), 200)
    expect('повторная блокировка -> 409', call('user', 'POST', f'/users/{buyer["id"]}:block'), 409)

    print()
    if failed:
        print(f'ПРОВАЛЕНО: {len(failed)}: {failed}')
        sys.exit(1)
    print('ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ')


if __name__ == '__main__':
    main()
