import logging

import logger_config


def test_log_file(monkeypatch, tmp_path):
    root = logging.getLogger()
    old_level = root.level
    monkeypatch.setattr(root, 'handlers', [])
    monkeypatch.setattr(logger_config, 'BASE_DIR', tmp_path)
    try:
        logger_config.setup_logger()
        logging.info('Проверка журнала')
        for handler in root.handlers:
            handler.flush()
        assert 'Проверка журнала' in (tmp_path / 'logs' / 'delivery.log').read_text(encoding='utf-8')
    finally:
        for handler in root.handlers:
            handler.close()
        root.setLevel(old_level)
