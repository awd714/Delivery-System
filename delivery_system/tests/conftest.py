import pytest

from database import Database
from models import Customer, Order


@pytest.fixture
def db():
    database = Database(':memory:')
    yield database
    database.close()


@pytest.fixture
def customer_id(db):
    return db.add_customer(Customer('Иван', '+70000000000', 'Москва'))


def make_order(customer_id, day='2026-11-26', status='новый', quantity=2, price=750):
    return Order(customer_id, day, status, [{'product_name': 'Пицца', 'quantity': quantity, 'price': price}])
