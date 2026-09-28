"""
ETL-процесс загрузки справочника акций в dwh.split.

Получает справочные данные MOEX, ограничивает их scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_splits
from moex_analytics.db.read import get_security_ids
from moex_analytics.db.write import upsert_split
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import (
    HISTORY_DATE_FROM,
    HISTORY_DATE_TO,
    SELECTED_SECURITIES,
)

logger = logging.getLogger(__name__)

SPLIT_COLUMNS = {
    "tradedate": "trade_date",
    "before": "ratio_before",
    "after": "ratio_after",
}


def get_split() -> pd.DataFrame:
    """Из  MOEX ISS выгружает все данные по сплитам и дроблениям акций.
    По условиям из scope оставляет только нужные акции в нужном периоде.
    """
    data = get_splits()
    df = pd.DataFrame(
        columns=data["splits"]["columns"],
        data=data["splits"]["data"],
    )
    df = df[df["secid"].isin(SELECTED_SECURITIES)]
    df["tradedate"] = pd.to_datetime(df["tradedate"])
    df = df[
        (df["tradedate"] >= pd.Timestamp(HISTORY_DATE_FROM))
        & (df["tradedate"] <= pd.Timestamp(HISTORY_DATE_TO))
    ]
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.split.
    Добавляет security_id для каждой акции."""

    security_ids = get_security_ids(list(df["secid"].unique()))
    df["security_id"] = df["secid"].map(security_ids)

    if df["security_id"].isna().any():
        missing_securities = (
            df.loc[df["security_id"].isna(), "secid"].drop_duplicates().tolist()
        )

        raise ValueError(f"Не найдены security_id для акций: {missing_securities}")

    df = df[["security_id", *SPLIT_COLUMNS.keys()]]
    df = df.rename(columns=SPLIT_COLUMNS)

    df["security_id"] = df["security_id"].astype("Int64")
    df["ratio_before"] = df["ratio_before"].astype("Int64")
    df["ratio_after"] = df["ratio_after"].astype("Int64")
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    return df


def load_split() -> None:
    logger.info("Начата выгрузка данных для dwh.split")
    df = get_split()
    if df.empty:
        logger.info("Данные по составу индексов отсутствуют.")
        return

    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_split(rows)
    logger.info("загрузка dwh.split завершена")


if __name__ == "__main__":
    setup_logging()
    load_split()
