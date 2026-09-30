"""
ETL-процесс загрузки справочника индексов в dwh.index.

Получает справочные данные MOEX, ограничивает их scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_stock_index
from moex_analytics.db.write import upsert_index
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import SELECTED_INDICES

logger = logging.getLogger(__name__)

INDEX_MAP = {
    "indexid": "index_code",
    "shortname": "short_name",
    "from": "analytics_from",
    "till": "analytics_till",
}


def get_index_data() -> pd.DataFrame:
    """Возвращает в табличном виде справочник индексов из MOEX ISS."""
    data = get_stock_index()
    df = pd.DataFrame(
        columns=data["indices"]["columns"],
        data=data["indices"]["data"],
    )
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.index."""
    df = df[df["indexid"].isin(SELECTED_INDICES)]
    df = df[list(SELECTED_INDICES.keys())]
    df = df.rename(columns=INDEX_MAP)

    df["analytics_from"] = pd.to_datetime(df["analytics_from"]).dt.date
    df["analytics_till"] = pd.to_datetime(df["analytics_till"]).dt.date
    return df


def load_indices() -> None:
    """Загружает и актуализирует справочник индексов в dwh.index."""
    logger.info("Начата загрузка справочника индексов dwh.index")
    df = get_index_data()
    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_index(rows)
    logger.info("Завершена загрузка справочника индексов dwh.index")


if __name__ == "__main__":
    setup_logging()
    load_indices()
