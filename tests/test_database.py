from datetime import date

import pytest

from database import Database, format_report
from models import Customer
from conftest import make_order


def test_customer_crud(db, customer_id):
    assert db.get_customer(customer_id)['name'] == 'Иван'
    db.update_customer(customer_id, Customer('Пётр', '123', 'Казань'))
    assert db.get_customers()[0]['address'] == 'Казань'
    db.delete_customer(customer_id)
    assert db.get_customers() == []
    assert db.get_customer(customer_id) is None
    with pytest.raises(ValueError):
        db.update_customer(customer_id, Customer('Пётр'))


def test_order_crud(db, customer_id):
    order_id = db.add_order(make_order(customer_id))
    assert db.get_order(order_id)['total'] == 1500
    assert db.get_orders()[0]['customer_name'] == 'Иван'
    db.update_order(order_id, make_order(customer_id, status='выполнен', quantity=1))
    updated = db.get_order(order_id)
    assert updated['status'] == 'выполнен'
    assert updated['items'][0]['quantity'] == 1
    assert updated['total'] == 750
    db.delete_order(order_id)
    assert db.get_order(order_id) is None
    assert db.conn.execute('SELECT COUNT(*) FROM order_items').fetchone()[0] == 0
    with pytest.raises(ValueError):
        db.update_order(order_id, make_order(customer_id))


def test_customer_delete_restriction(db, customer_id):
    order_id = db.add_order(make_order(customer_id))
    with pytest.raises(ValueError):
        db.delete_customer(customer_id)
    assert db.get_customer(customer_id) is not None
    db.delete_order(order_id)
    db.delete_customer(customer_id)
    assert db.get_customer(customer_id) is None


def test_missing_customer(db, customer_id):
    with pytest.raises(ValueError):
        db.add_order(make_order(999))
    order_id = db.add_order(make_order(customer_id))
    with pytest.raises(ValueError):
        db.update_order(order_id, make_order(999))


def test_filters(db, customer_id):
    first = db.add_order(make_order(customer_id, '2026-11-25', 'новый'))
    second = db.add_order(make_order(customer_id, '2026-11-26', 'выполнен'))
    assert [row['id'] for row in db.get_orders(status='новый')] == [first]
    assert [row['id'] for row in db.get_orders(start='2026-11-26', end='2026-11-26')] == [second]
    assert db.get_orders(status='новый', start='2026-11-26') == []


def test_report(db, customer_id):
    db.add_order(make_order(customer_id, '2026-11-26', 'выполнен'))
    db.add_order(make_order(customer_id, '2026-11-24', 'выполнен'))
    db.add_order(make_order(customer_id, '2026-11-02', 'выполнен'))
    db.add_order(make_order(customer_id, '2026-10-01', 'выполнен'))
    db.add_order(make_order(customer_id, '2026-11-26', 'отменён'))
    for name, price in [('Анна', 100), ('Олег', 200), ('Пётр', 300)]:
        db.add_order(make_order(db.add_customer(Customer(name)), price=price))
    today = date(2026, 11, 26)
    assert db.report('day', today)['revenue'] == 1500
    assert db.report('week', today)['revenue'] == 3000
    result = db.report('month', today)
    assert result['revenue'] == 4500
    assert result['counts'] == {'новый': 3, 'в доставке': 0, 'выполнен': 4, 'отменён': 1}
    assert [row['name'] for row in result['top']] == ['Иван', 'Пётр', 'Олег']
    assert '4500.00' in format_report(result)
    with pytest.raises(ValueError):
        db.report('year')


def test_database_file(tmp_path):
    path = tmp_path / 'data' / 'test.db'
    db = Database(path)
    db.add_customer(Customer('Анна'))
    db.close()
    reopened = Database(path)
    assert reopened.get_customers()[0]['name'] == 'Анна'
    reopened.close()
