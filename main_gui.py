import logging
import sqlite3
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from database import Database, format_report
from logger_config import setup_logger
from models import Customer, Order, STATUSES


class App:
    def __init__(self, root, db):
        self.root = root
        self.db = db
        root.title('Быстрая доставка — учёт заказов')
        root.geometry('920x540')

        filters = ttk.Frame(root)
        filters.pack(fill='x', padx=10, pady=10)
        ttk.Label(filters, text='Статус:').pack(side='left')
        self.status = ttk.Combobox(filters, values=('Все',) + STATUSES, state='readonly', width=15)
        self.status.set('Все')
        self.status.pack(side='left', padx=5)
        ttk.Label(filters, text='С даты:').pack(side='left')
        self.start = ttk.Entry(filters, width=12)
        self.start.pack(side='left', padx=5)
        ttk.Label(filters, text='По дату:').pack(side='left')
        self.end = ttk.Entry(filters, width=12)
        self.end.pack(side='left', padx=5)
        ttk.Button(filters, text='Фильтр', command=self.refresh).pack(side='left', padx=5)
        ttk.Button(filters, text='Сбросить', command=self.reset_filters).pack(side='left')

        self.tree = self.make_table(root, ('id', 'date', 'customer', 'status', 'total'),
                                    ('ID', 'Дата', 'Клиент', 'Статус', 'Сумма'), (55, 115, 230, 140, 110))
        buttons = ttk.Frame(root)
        buttons.pack(fill='x', padx=10, pady=10)
        for title, command in [('Добавить', self.order_form), ('Редактировать', self.edit_order),
                               ('Удалить', self.delete_order), ('Клиенты', self.customers_window),
                               ('Показать отчёт', self.show_report)]:
            ttk.Button(buttons, text=title, command=command).pack(side='left', padx=3)
        self.tree.bind('<Double-1>', lambda event: self.edit_order())
        self.refresh()

    def make_table(self, parent, columns, headings, widths):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=10, pady=5)
        tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='browse')
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', fill='both', expand=True)
        for column, title, width in zip(columns, headings, widths):
            tree.heading(column, text=title)
            tree.column(column, width=width)
        return tree

    def selected_id(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showinfo('Выбор', 'Выберите строку в таблице')
            return None
        return int(selected[0])

    def error(self, error):
        logging.error('%s', error)
        messagebox.showerror('Ошибка', str(error))

    def refresh(self):
        start = self.start.get().strip()
        end = self.end.get().strip()
        status = self.status.get()
        try:
            for value in (start, end):
                if value and date.fromisoformat(value).isoformat() != value:
                    raise ValueError('Формат даты: ГГГГ-ММ-ДД')
            if start and end and start > end:
                raise ValueError('Начальная дата позже конечной')
            rows = self.db.get_orders('' if status == 'Все' else status, start, end)
        except (ValueError, sqlite3.Error) as error:
            self.error(error)
            return
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert('', 'end', iid=str(row['id']), values=(row['id'], row['order_date'],
                             row['customer_name'], row['status'], f"{row['total']:.2f}"))

    def reset_filters(self):
        self.status.set('Все')
        self.start.delete(0, 'end')
        self.end.delete(0, 'end')
        self.refresh()

    def order_form(self, order_id=None):
        customers = self.db.get_customers()
        if not customers:
            messagebox.showinfo('Клиенты', 'Сначала добавьте клиента')
            return
        order = self.db.get_order(order_id) if order_id is not None else None
        win = tk.Toplevel(self.root)
        win.title('Заказ')
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text='Клиент').pack(pady=(10, 0))
        names = [f"{row['id']} — {row['name']}" for row in customers]
        customer = ttk.Combobox(win, values=names, state='readonly', width=42)
        customer.pack(padx=15)
        customer.current(0)
        if order:
            for index, row in enumerate(customers):
                if row['id'] == order['customer_id']:
                    customer.current(index)
        ttk.Label(win, text='Дата (ГГГГ-ММ-ДД)').pack()
        day = ttk.Entry(win, width=44)
        day.pack()
        day.insert(0, order['order_date'] if order else date.today().isoformat())
        ttk.Label(win, text='Статус').pack()
        status = ttk.Combobox(win, values=STATUSES, state='readonly', width=42)
        status.pack()
        status.set(order['status'] if order else 'новый')
        ttk.Label(win, text='Товары: название|количество|цена (по одному на строку)').pack(padx=10, pady=(10, 0))
        items = tk.Text(win, width=50, height=7)
        items.pack(padx=15)
        if order:
            for item in order['items']:
                items.insert('end', f"{item['product_name']}|{item['quantity']}|{item['price']}\n")
        ttk.Label(win, text='Сумма рассчитывается автоматически').pack()

        def save():
            try:
                products = []
                for line in items.get('1.0', 'end').strip().splitlines():
                    if line.strip():
                        name, quantity, price = line.split('|')
                        products.append({'product_name': name, 'quantity': int(quantity), 'price': float(price.replace(',', '.'))})
                new_order = Order(customers[customer.current()]['id'], day.get().strip(), status.get(), products)
                if order_id is None:
                    self.db.add_order(new_order)
                else:
                    self.db.update_order(order_id, new_order)
                win.destroy()
                self.reset_filters()
            except (ValueError, sqlite3.Error, OverflowError) as error:
                self.error(error)

        ttk.Button(win, text='Сохранить', command=save).pack(pady=10)
        return win

    def edit_order(self):
        order_id = self.selected_id(self.tree)
        if order_id is not None:
            self.order_form(order_id)

    def delete_order(self):
        order_id = self.selected_id(self.tree)
        if order_id is not None and messagebox.askyesno('Удаление', 'Удалить выбранный заказ?'):
            try:
                self.db.delete_order(order_id)
                self.refresh()
            except sqlite3.Error as error:
                self.error(error)

    def customers_window(self):
        win = tk.Toplevel(self.root)
        win.title('Клиенты')
        win.geometry('690x380')
        win.transient(self.root)
        tree = self.make_table(win, ('id', 'name', 'phone', 'address'),
                               ('ID', 'Имя', 'Телефон', 'Адрес'), (50, 180, 130, 230))

        def refresh():
            tree.delete(*tree.get_children())
            for row in self.db.get_customers():
                tree.insert('', 'end', iid=str(row['id']), values=(row['id'], row['name'], row['phone'], row['address']))
            self.refresh()

        def form(edit=False):
            customer_id = self.selected_id(tree) if edit else None
            if edit and customer_id is None:
                return
            row = self.db.get_customer(customer_id) if edit else None
            name = simpledialog.askstring('Клиент', 'Имя:', initialvalue=row['name'] if row else '', parent=win)
            if name is None:
                return
            phone = simpledialog.askstring('Клиент', 'Телефон:', initialvalue=row['phone'] if row else '', parent=win)
            if phone is None:
                return
            address = simpledialog.askstring('Клиент', 'Адрес:', initialvalue=row['address'] if row else '', parent=win)
            if address is None:
                return
            try:
                customer = Customer(name, phone, address)
                if edit:
                    self.db.update_customer(customer_id, customer)
                else:
                    self.db.add_customer(customer)
                refresh()
            except (ValueError, sqlite3.Error) as error:
                self.error(error)

        def delete():
            customer_id = self.selected_id(tree)
            if customer_id is not None and messagebox.askyesno('Удаление', 'Удалить клиента?', parent=win):
                try:
                    self.db.delete_customer(customer_id)
                    refresh()
                except (ValueError, sqlite3.Error) as error:
                    self.error(error)

        buttons = ttk.Frame(win)
        buttons.pack(pady=10)
        ttk.Button(buttons, text='Добавить', command=form).pack(side='left', padx=5)
        ttk.Button(buttons, text='Редактировать', command=lambda: form(True)).pack(side='left', padx=5)
        ttk.Button(buttons, text='Удалить', command=delete).pack(side='left', padx=5)
        refresh()
        return win

    def show_report(self):
        win = tk.Toplevel(self.root)
        win.title('Отчёт')
        ttk.Label(win, text='Период выручки:').pack(padx=15, pady=5)
        period = ttk.Combobox(win, values=('День', 'Неделя', 'Месяц'), state='readonly')
        period.current(2)
        period.pack()
        label = ttk.Label(win, justify='left')
        label.pack(padx=20, pady=15)

        def refresh():
            label.configure(text=format_report(self.db.report(('day', 'week', 'month')[period.current()])))
        ttk.Button(win, text='Обновить', command=refresh).pack(pady=10)
        refresh()
        return win


def main():
    setup_logger()
    db = Database()
    try:
        root = tk.Tk()
        App(root, db)
        logging.info('Запущен графический режим')
        root.mainloop()
    finally:
        db.close()


if __name__ == '__main__':
    main()
