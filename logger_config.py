import logging
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def setup_logger():
    folder = BASE_DIR / 'logs'
    folder.mkdir(exist_ok=True)
    logging.basicConfig(
        handlers=[logging.FileHandler(folder / 'delivery.log', encoding='utf-8')],
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
