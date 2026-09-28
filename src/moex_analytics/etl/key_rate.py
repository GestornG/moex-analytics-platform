"""
ETL-процесс загрузки данмики изменения ключевой ставки ЦБ dwh.key_rate .

Получает данные www.cbr.ru за период из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging
from io import BytesIO

import pandas as pd

from moex_analytics.api.cb import get_key_rate
from moex_analytics.db.write import upsert_key_rate
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import HISTORY_DATE_FROM, HISTORY_DATE_TO

logger = logging.getLogger(__name__)

COLUMNS_NAME = {
    "DT": "rate_date",
    "Rate": "rate",
}


def get_key_rate_dataframe() -> pd.DataFrame:
    """Получает данные по ключевой ставке за весь период и преобразует данные
    в pd.DataFrame"""
    data = get_key_rate(date_from=HISTORY_DATE_FROM, date_to=HISTORY_DATE_TO)

    df = pd.read_xml(BytesIO(data), xpath=".//KR", parser="etree", encoding="utf-8")
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные ЦБ к структуре dwh.key_rate."""
    df = df[list(COLUMNS_NAME.keys())]
    df = df.rename(columns=COLUMNS_NAME)

    df["rate_date"] = pd.to_datetime(df["rate_date"]).dt.date
    df["rate"] = pd.to_numeric(df["rate"])
    return df


def load_key_rate() -> None:
    logger.info("Начата выгрузка данных для dwh.key_rate")
    df = get_key_rate_dataframe()
    if df.empty:
        logger.warning("Данные по ключевой ставке отсутствуют.")
        return

    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_key_rate(rows)
    logger.info("Загрузка dwh.key_rate завершена")


if __name__ == "__main__":
    setup_logging()
    load_key_rate()
