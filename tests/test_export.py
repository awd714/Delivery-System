import json

import pytest

from database import Database
from data_export import export_orders, import_orders
from models import Customer
from conftest import make_order


def test_roundtrip(db, customer_id, tmp_path):
    order_id = db.add_order(make_order(customer_id))
    second = db.add_customer(Customer('Анна'))
    db.add_order(make_order(second, status='в доставке'))
    path = tmp_path / 'orders.json'
    assert export_orders(db, path) == 2
    restored = Database(':memory:')
    try:
        assert import_orders(restored, path) == 2
        assert restored.get_order(order_id) == db.get_order(order_id)
        assert restored.get_customers() == db.get_customers()
        assert import_orders(restored, path) == 0
    finally:
        restored.close()


def test_invalid_json(db, tmp_path):
    path = tmp_path / 'bad.json'
    path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    path.write_text('{"orders":[{}]}', encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    path.write_text('{"orders":42}', encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)


def test_wrong_extension(db, tmp_path):
    with pytest.raises(ValueError):
        export_orders(db, tmp_path / 'orders.txt')
    with pytest.raises(ValueError):
        import_orders(db, tmp_path / 'orders.txt')


def test_invalid_total_and_duplicates(db, customer_id, tmp_path):
    order_id = db.add_order(make_order(customer_id))
    path = tmp_path / 'orders.json'
    export_orders(db, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['orders'][0]['total'] = 1
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    data['orders'][0]['total'] = 1500
    data['orders'].append(data['orders'][0])
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    assert db.get_order(order_id)['total'] == 1500


def test_atomic_import(db, customer_id, tmp_path):
    order_id = db.add_order(make_order(customer_id))
    path = tmp_path / 'orders.json'
    export_orders(db, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    first = data['orders'][0]
    new = dict(first, id=2, customer_id=2, customer={'id': 2, 'name': 'Анна'})
    conflict = dict(first, status='отменён')
    path.write_text(json.dumps({'orders': [new, conflict]}), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    assert db.get_order(2) is None
    assert db.get_customer(2) is None
    assert db.get_order(order_id)['status'] == 'новый'
    missing = dict(first, id=3, customer_id=99)
    missing.pop('customer')
    path.write_text(json.dumps({'orders': [missing]}), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
    conflict = dict(first, customer={'name': 'Анна'})
    path.write_text(json.dumps({'orders': [conflict]}), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)


def test_customer_id_mismatch(db, customer_id, tmp_path):
    db.add_order(make_order(customer_id))
    path = tmp_path / 'orders.json'
    export_orders(db, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['orders'][0]['customer']['id'] = 99
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        import_orders(db, path)
