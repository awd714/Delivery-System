from datetime import date
from math import isfinite


STATUSES = ('новый', 'в доставке', 'выполнен', 'отменён')
MAX_ID = 2 ** 63 - 1


class Customer:
    def __init__(self, name, phone='', address=''):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Введите имя клиента')
        if not isinstance(phone, str) or not isinstance(address, str):
            raise ValueError('Телефон и адрес должны быть строками')
        self.name = name.strip()
        self.phone = phone.strip()
        self.address = address.strip()


class Order:
    def __init__(self, customer_id, order_date, status, items):
        if type(customer_id) != int or not 0 < customer_id <= MAX_ID:
            raise ValueError('Неверный номер клиента')
        if not isinstance(order_date, str):
            raise ValueError('Введите дату в формате ГГГГ-ММ-ДД')
        try:
            day = date.fromisoformat(order_date)
        except ValueError:
            raise ValueError('Введите дату в формате ГГГГ-ММ-ДД')
        if day.isoformat() != order_date:
            raise ValueError('Введите дату в формате ГГГГ-ММ-ДД')
        if status not in STATUSES:
            raise ValueError('Неверный статус заказа')
        if not isinstance(items, list) or not items:
            raise ValueError('Добавьте хотя бы один товар')

        self.customer_id = customer_id
        self.order_date = order_date
        self.status = status
        self.items = []

        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Неверный формат товара')
            name = item.get('product_name')
            quantity = item.get('quantity')
            price = item.get('price')
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Введите название товара')
            if '|' in name or '\n' in name or '\r' in name:
                raise ValueError('Название товара не должно содержать | или перенос строки')
            if type(quantity) != int or not 0 < quantity <= MAX_ID:
                raise ValueError('Количество должно быть целым положительным числом')
            if type(price) not in (int, float) or not isfinite(price) or price < 0:
                raise ValueError('Неверная цена товара')
            self.items.append({'product_name': name.strip(), 'quantity': quantity,
                               'price': round(float(price), 2)})

        self.total = round(sum(item['quantity'] * item['price'] for item in self.items), 2)
        if not isfinite(self.total):
            raise ValueError('Слишком большая сумма заказа')
