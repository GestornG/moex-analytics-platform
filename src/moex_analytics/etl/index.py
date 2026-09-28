"""
ETL-процесс загрузки справочника акций в dwh.index.

Получает справочные данные MOEX, ограничивает их scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_stock_index
from moex_analytics.db.write import upsert_index
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.settings import SELECTED_INDICES

logger = logging.getLogger(__name__)

INDEX_MAP = {
    "indexid": "index_code",
    "shortname": "short_name",
    "from": "analytics_from",
    "till": "analytics_till",
}


def get_index_datad() -> pd.DataFrame:
    """Возвращает в табличном виде справочник индексов из MOEX ISS."""
    data = get_stock_index()
    df = pd.DataFrame(
        columns=data["indices"]["columns"],
        data=data["indices"]["data"],
    )
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.index."""
    df = df[df["indexid"].isin(list(SELECTED_INDICES.keys()))]
    df = df.rename(columns=INDEX_MAP)

    df["analytics_from"] = pd.to_datetime(df["analytics_from"]).dt.date
    df["analytics_till"] = pd.to_datetime(df["analytics_till"]).dt.date
    return df


def dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса."""
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        row = dict(zip(columns, values))
        rows.append(row)
    return rows


def load_indices() -> None:
    """Загружает и актуализирует справочник акций в dwh.index."""
    logger.info("Начата загрузка справочника акций dwh.index")
    df = get_index_datad()
    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_index(rows)
    logger.info("Завершена загрузка справочника акций dwh.index")


if __name__ == "__main__":
    load_indices()
