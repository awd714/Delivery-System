import sys

import main_cli
from database import Database
from models import Customer
from conftest import make_order


def test_cli(monkeypatch, tmp_path, capsys):
    filename = tmp_path / 'test.db'
    db = Database(filename)
    db.add_order(make_order(db.add_customer(Customer('Анна'))))
    db.close()
    monkeypatch.setattr(main_cli, 'Database', lambda: Database(filename))
    monkeypatch.setattr(main_cli, 'setup_logger', lambda: None)
    path = tmp_path / 'orders.json'
    for args, expected in [(['report', '--period', 'month'], 'Заказы по статусам'),
                           (['export', '--file', str(path)], 'Экспортировано заказов: 1'),
                           (['import', '--file', str(path)], 'Добавлено заказов: 0')]:
        monkeypatch.setattr(sys, 'argv', ['main_cli.py'] + args)
        assert main_cli.main() == 0
        assert expected in capsys.readouterr().out
    monkeypatch.setattr(sys, 'argv', ['main_cli.py', 'import', '--file', 'missing.json'])
    assert main_cli.main() == 1
    assert 'Ошибка:' in capsys.readouterr().out


def test_delivery_entrypoint(monkeypatch, tmp_path, capsys):
    import runpy
    import pytest

    monkeypatch.setattr(main_cli, 'Database', lambda: Database(tmp_path / 'test.db'))
    monkeypatch.setattr(main_cli, 'setup_logger', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['delivery.py', 'report', '--period', 'day'])
    with pytest.raises(SystemExit) as error:
        runpy.run_module('delivery', run_name='__main__')
    assert error.value.code == 0
    assert 'Выручка' in capsys.readouterr().out
