"""
Верхнеуровневый оркестровый модуль ETL процесса выгрузки исходных данных и загрузки
в таблицы базы данных, схемы dwh.
"""

import logging

from moex_analytics.api.tbank import check_t_invest_token
from moex_analytics.etl.calendar_etl import load_calendar
from moex_analytics.etl.candle_1m import load_candle_1m
from moex_analytics.etl.currency import load_currency
from moex_analytics.etl.currency_rate import load_currency_rate
from moex_analytics.etl.dividend import load_dividend
from moex_analytics.etl.index import load_indices
from moex_analytics.etl.index_composition import load_index_composition
from moex_analytics.etl.index_daily import load_index_daily
from moex_analytics.etl.key_rate import load_key_rate
from moex_analytics.etl.security import load_security
from moex_analytics.etl.security_daily import load_security_daily
from moex_analytics.etl.split import load_split
from moex_analytics.logging_config import setup_logging

logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    logger.info("Запуск ETL pipeline")

    # Проверка корректности и актуальности токена ТБанка
    token: bool = check_t_invest_token()

    # Справочники
    load_indices()
    load_security(t_token_available=token)
    load_currency()
    load_calendar()

    # Исторические данные
    load_index_daily()
    load_security_daily()
    load_candle_1m()
    load_currency_rate()
    load_key_rate()

    # Связанные сущности и события
    load_index_composition()
    load_split()

    if token:
        load_dividend()
    else:
        logger.warning("Загрузка дивидендов пропущена: T-Invest недоступен")

    logger.info("ETL pipeline завершён")


if __name__ == "__main__":
    setup_logging()
    run_pipeline()
