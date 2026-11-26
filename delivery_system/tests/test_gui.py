import tkinter as tk
from tkinter import ttk

import pytest

import main_gui
from models import Customer
from conftest import make_order


@pytest.fixture
def app(db, monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('Для теста Tkinter нужен графический экран')
    monkeypatch.setattr(main_gui.messagebox, 'showinfo', lambda *a, **kw: None)
    monkeypatch.setattr(main_gui.messagebox, 'showerror', lambda *a, **kw: None)
    monkeypatch.setattr(main_gui.messagebox, 'askyesno', lambda *a, **kw: True)
    yield main_gui.App(root, db)
    root.destroy()


def button(parent, text):
    for widget in parent.winfo_children():
        if isinstance(widget, ttk.Button) and widget.cget('text') == text:
            return widget
        found = button(widget, text)
        if found is not None:
            return found
    return None


def test_order_gui(app, db, customer_id):
    assert app.selected_id(app.tree) is None
    win = app.order_form()
    items = next(widget for widget in win.winfo_children() if isinstance(widget, tk.Text))
    items.insert('1.0', 'Чай|2|10')
    button(win, 'Сохранить').invoke()
    assert len(db.get_orders()) == 1
    assert db.get_orders()[0]['total'] == 20
    order_id = db.get_orders()[0]['id']
    app.tree.selection_set(str(order_id))
    app.edit_order()
    win = next(widget for widget in app.root.winfo_children() if isinstance(widget, tk.Toplevel))
    items = next(widget for widget in win.winfo_children() if isinstance(widget, tk.Text))
    items.delete('1.0', 'end')
    items.insert('1.0', 'Чай|3|10')
    button(win, 'Сохранить').invoke()
    assert db.get_order(order_id)['total'] == 30
    app.status.set('выполнен')
    app.refresh()
    assert not app.tree.get_children()
    app.reset_filters()
    app.tree.selection_set(str(order_id))
    app.delete_order()
    assert not db.get_orders()


def test_customers_gui(app, db, monkeypatch):
    assert app.order_form() is None
    win = app.customers_window()
    answers = iter(['Анна', '123', 'Москва'])
    monkeypatch.setattr(main_gui.simpledialog, 'askstring', lambda *a, **kw: next(answers))
    button(win, 'Добавить').invoke()
    customer_id = db.get_customers()[0]['id']
    tree = next(widget for frame in win.winfo_children() for widget in frame.winfo_children() if isinstance(widget, ttk.Treeview))
    tree.selection_set(str(customer_id))
    answers = iter(['Ольга', '456', 'Казань'])
    button(win, 'Редактировать').invoke()
    assert db.get_customer(customer_id)['name'] == 'Ольга'
    tree.selection_set(str(customer_id))
    db.add_order(make_order(customer_id))
    button(win, 'Удалить').invoke()
    assert db.get_customer(customer_id) is not None
    db.delete_order(db.get_orders()[0]['id'])
    button(win, 'Удалить').invoke()
    assert db.get_customer(customer_id) is None


def test_report_gui(app, db, customer_id):
    db.add_order(make_order(customer_id))
    win = app.show_report()
    button(win, 'Обновить').invoke()
    app.start.insert(0, 'bad')
    app.refresh()
    app.reset_filters()
