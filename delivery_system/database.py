import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from models import Customer, Order, STATUSES


DB_FILE = Path(__file__).resolve().parent / 'data' / 'delivery.db'


class Database:
    def __init__(self, filename=DB_FILE):
        if filename != ':memory:':
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('новый','в доставке','выполнен','отменён')),
                total REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                price REAL NOT NULL CHECK(price >= 0)
            );
        ''')

    def close(self):
        self.conn.close()

    def get_customers(self):
        return [dict(row) for row in self.conn.execute('SELECT * FROM customers ORDER BY id')]

    def get_customer(self, customer_id):
        row = self.conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
        return dict(row) if row else None

    def _insert_customer(self, customer, customer_id=None):
        result = self.conn.execute(
            'INSERT INTO customers VALUES (?, ?, ?, ?)',
            (customer_id, customer.name, customer.phone, customer.address))
        return result.lastrowid

    def add_customer(self, customer):
        with self.conn:
            customer_id = self._insert_customer(customer)
        logging.info('Добавлен клиент %s', customer_id)
        return customer_id

    def update_customer(self, customer_id, customer):
        with self.conn:
            result = self.conn.execute('UPDATE customers SET name=?, phone=?, address=? WHERE id=?',
                                       (customer.name, customer.phone, customer.address, customer_id))
            if not result.rowcount:
                raise ValueError('Клиент не найден')
        logging.info('Изменён клиент %s', customer_id)

    def delete_customer(self, customer_id):
        try:
            with self.conn:
                self.conn.execute('DELETE FROM customers WHERE id=?', (customer_id,))
        except sqlite3.IntegrityError:
            raise ValueError('Нельзя удалить клиента, у которого есть заказы')
        logging.info('Удалён клиент %s', customer_id)

    def get_orders(self, status='', start='', end=''):
        sql = '''SELECT orders.*, customers.name AS customer_name FROM orders
                 JOIN customers ON orders.customer_id = customers.id WHERE 1=1'''
        params = []
        if status:
            sql += ' AND status = ?'
            params.append(status)
        if start:
            sql += ' AND order_date >= ?'
            params.append(start)
        if end:
            sql += ' AND order_date <= ?'
            params.append(end)
        sql += ' ORDER BY order_date DESC, orders.id DESC'
        return [dict(row) for row in self.conn.execute(sql, params)]

    def get_order(self, order_id):
        row = self.conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        if row is None:
            return None
        order = dict(row)
        order['items'] = [dict(item) for item in self.conn.execute(
            'SELECT product_name, quantity, price FROM order_items WHERE order_id=? ORDER BY id',
            (order_id,))]
        return order

    def _save_items(self, order_id, items):
        for item in items:
            self.conn.execute('INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)',
                              (order_id, item['product_name'], item['quantity'], item['price']))

    def _insert_order(self, order, order_id=None):
        if self.get_customer(order.customer_id) is None:
            raise ValueError('Клиент не найден')
        result = self.conn.execute('INSERT INTO orders VALUES (?, ?, ?, ?, ?)',
                                   (order_id, order.customer_id, order.order_date, order.status, order.total))
        order_id = result.lastrowid
        self._save_items(order_id, order.items)
        return order_id

    def add_order(self, order):
        with self.conn:
            order_id = self._insert_order(order)
        logging.info('Добавлен заказ %s', order_id)
        return order_id

    def update_order(self, order_id, order):
        with self.conn:
            if self.get_customer(order.customer_id) is None:
                raise ValueError('Клиент не найден')
            result = self.conn.execute('UPDATE orders SET customer_id=?, order_date=?, status=?, total=? WHERE id=?',
                                       (order.customer_id, order.order_date, order.status, order.total, order_id))
            if not result.rowcount:
                raise ValueError('Заказ не найден')
            self.conn.execute('DELETE FROM order_items WHERE order_id=?', (order_id,))
            self._save_items(order_id, order.items)
        logging.info('Изменён заказ %s', order_id)

    def delete_order(self, order_id):
        with self.conn:
            self.conn.execute('DELETE FROM orders WHERE id=?', (order_id,))
        logging.info('Удалён заказ %s', order_id)

    def report(self, period, today=None):
        if today is None:
            today = date.today()
        if period == 'day':
            start = today
        elif period == 'week':
            start = today - timedelta(days=today.weekday())
        elif period == 'month':
            start = today.replace(day=1)
        else:
            raise ValueError('Неизвестный период')

        counts = dict.fromkeys(STATUSES, 0)
        for row in self.conn.execute('SELECT status, COUNT(*) AS amount FROM orders GROUP BY status'):
            counts[row['status']] = row['amount']
        top = self.conn.execute('''SELECT customers.name, SUM(orders.total) AS total
                                   FROM orders JOIN customers ON customers.id = orders.customer_id
                                   GROUP BY customers.id ORDER BY total DESC, customers.id LIMIT 3''').fetchall()
        revenue = self.conn.execute('''SELECT COALESCE(SUM(total), 0) FROM orders
                                       WHERE status='выполнен' AND order_date BETWEEN ? AND ?''',
                                    (start.isoformat(), today.isoformat())).fetchone()[0]
        return {'counts': counts, 'top': [dict(row) for row in top], 'revenue': round(revenue, 2),
                'start': start.isoformat(), 'end': today.isoformat()}

    def import_orders(self, records):
        added = 0
        with self.conn:
            for order_id, order, customer in records:
                existing_customer = self.get_customer(order.customer_id)
                if existing_customer is None:
                    if customer is None:
                        raise ValueError('Клиент для заказа не найден')
                    self._insert_customer(customer, order.customer_id)
                elif customer is not None and (existing_customer['name'], existing_customer['phone'], existing_customer['address']) != (customer.name, customer.phone, customer.address):
                    raise ValueError('Номер клиента уже занят другими данными')

                existing = self.get_order(order_id)
                if existing is not None:
                    expected = {'id': order_id, 'customer_id': order.customer_id, 'order_date': order.order_date,
                                'status': order.status, 'total': order.total, 'items': order.items}
                    if existing != expected:
                        raise ValueError('Номер заказа уже занят другими данными')
                else:
                    self._insert_order(order, order_id)
                    added += 1
        logging.info('Импортировано заказов: %s', added)
        return added


def format_report(report):
    lines = ['Заказы по статусам (за всё время):']
    for status, count in report['counts'].items():
        lines.append(f'{status}: {count}')
    lines.append('\nТоп-3 клиента по сумме заказов (за всё время):')
    for customer in report['top']:
        lines.append(f"{customer['name']}: {customer['total']:.2f}")
    lines.append(f"\nВыручка за {report['start']} — {report['end']}: {report['revenue']:.2f}")
    return '\n'.join(lines)
