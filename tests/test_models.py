import pytest

from models import Customer, Order
from conftest import make_order


def test_customer():
    customer = Customer(' Иван ', ' 123 ', ' Москва ')
    assert (customer.name, customer.phone, customer.address) == ('Иван', '123', 'Москва')


@pytest.mark.parametrize('name,phone,address', [('', '', ''), (None, '', ''), ('Иван', 123, '')])
def test_bad_customer(name, phone, address):
    with pytest.raises(ValueError):
        Customer(name, phone, address)


def test_order_total():
    order = Order(1, '2026-11-26', 'новый', [
        {'product_name': 'Пицца', 'quantity': 2, 'price': 750},
        {'product_name': 'Чай', 'quantity': 3, 'price': 20.15}])
    assert order.total == 1560.45
    assert len(order.items) == 2


@pytest.mark.parametrize('customer,day,status,items', [
    (0, '2026-11-26', 'новый', []),
    (1, None, 'новый', []),
    (1, '2026-02-30', 'новый', []),
    (1, '20261126', 'новый', []),
    (1, '2026-11-26', 'другой', []),
    (1, '2026-11-26', 'новый', []),
    (1, '2026-11-26', 'новый', ['товар']),
    (1, '2026-11-26', 'новый', [{'product_name': '', 'quantity': 1, 'price': 2}]),
    (1, '2026-11-26', 'новый', [{'product_name': 'Чай', 'quantity': 0, 'price': 2}]),
    (1, '2026-11-26', 'новый', [{'product_name': 'Чай', 'quantity': 1, 'price': -2}]),
    (1, '2026-11-26', 'новый', [{'product_name': 'Чай', 'quantity': 1, 'price': float('nan')}]),
])
def test_bad_order(customer, day, status, items):
    with pytest.raises(ValueError):
        Order(customer, day, status, items)


def test_rounding():
    assert make_order(1, quantity=3, price=0.1).total == 0.3


def test_invalid_product_separator():
    with pytest.raises(ValueError):
        Order(1, '2026-11-26', 'новый', [{'product_name': 'Чай|кофе', 'quantity': 1, 'price': 2}])


def test_total_overflow():
    with pytest.raises(ValueError):
        make_order(1, quantity=2, price=1e308)
