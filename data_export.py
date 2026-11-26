import json
import logging
from pathlib import Path
from math import isfinite

from models import Customer, Order, MAX_ID


def export_orders(db, filename):
    orders = []
    for row in db.get_orders():
        order = db.get_order(row['id'])
        order['customer'] = db.get_customer(order['customer_id'])
        orders.append(order)

    if Path(filename).suffix.lower() != '.json':
        raise ValueError('Поддерживается только JSON')
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump({'orders': orders}, file, ensure_ascii=False, indent=4)
    logging.info('Экспортировано заказов: %s', len(orders))
    return len(orders)


def import_orders(db, filename):
    if Path(filename).suffix.lower() != '.json':
        raise ValueError('Поддерживается только JSON')
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            orders = json.load(file)['orders']
        if not isinstance(orders, list):
            raise ValueError('Ожидается список заказов')
        records = []
        ids = set()
        for row in orders:
            order_id = row['id']
            if type(order_id) != int or not 0 < order_id <= MAX_ID or order_id in ids:
                raise ValueError('Неверный или повторяющийся номер заказа')
            ids.add(order_id)
            order = Order(row['customer_id'], row['order_date'], row['status'], row['items'])
            total = row['total']
            if type(total) not in (int, float) or not isfinite(total) or abs(total - order.total) > 0.000001:
                raise ValueError('Итоговая сумма не совпадает с суммой товаров')
            customer = None
            if 'customer' in row:
                data = row['customer']
                if 'id' in data and data['id'] != order.customer_id:
                    raise ValueError('Номер клиента не совпадает')
                customer = Customer(data['name'], data.get('phone', ''), data.get('address', ''))
            records.append((order_id, order, customer))
    except (KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ValueError('Некорректный файл заказов') from error
    return db.import_orders(records)
