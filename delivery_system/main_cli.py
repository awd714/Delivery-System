import argparse
import logging
import sqlite3

from database import Database, format_report
from data_export import export_orders, import_orders
from logger_config import setup_logger


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description='Быстрая доставка')
    commands = parser.add_subparsers(dest='command', required=True)
    report = commands.add_parser('report', help='Показать отчёт')
    report.add_argument('--period', choices=['day', 'week', 'month'], default='month')
    commands.add_parser('export', help='Экспортировать заказы').add_argument('--file', required=True)
    commands.add_parser('import', help='Импортировать заказы').add_argument('--file', required=True)
    args = parser.parse_args()
    db = Database()
    try:
        if args.command == 'report':
            print(format_report(db.report(args.period)))
            logging.info('Сформирован отчёт: %s', args.period)
        elif args.command == 'export':
            print('Экспортировано заказов:', export_orders(db, args.file))
        elif args.command == 'import':
            print('Добавлено заказов:', import_orders(db, args.file))
        return 0
    except (OSError, ValueError, OverflowError, sqlite3.Error) as error:
        logging.error('%s', error)
        print('Ошибка:', error)
        return 1
    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main())
