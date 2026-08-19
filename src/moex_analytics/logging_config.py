import logging

from moex_analytics.settings import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "moex_analytics.log"


def setup_logging() -> None:
    """Настраивает вывод логов в консоль и файл."""
    LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            console_handler,
            file_handler,
        ],
    )
