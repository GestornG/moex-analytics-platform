"""
ETL-процесс загрузки истории участия акций в выбранных индексах
Московской биржи dwh.index_composition.

Получает данные MOEX по списку индексов и акций из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_index_composition
from moex_analytics.db.read import get_index_ids, get_security_ids
from moex_analytics.db.write import upsert_index_composition
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import SELECTED_INDICES, SELECTED_SECURITIES

logger = logging.getLogger(__name__)


def get_moex_index_composition() -> pd.DataFrame:
    """По списку индексов выгружает входящие в них акции и период их вхождения.
    По каждому индексу оставляет только акции из scope проекта.
    Возвращает:
        pd.DataFrame с именем индекса, акции и периодом вхождения (from - till).
    """

    dfs_index: list[pd.DataFrame] = []
    for index in SELECTED_INDICES:
        data = get_index_composition(index)
        df = pd.DataFrame(
            columns=data["tickers"]["columns"],
            data=data["tickers"]["data"],
        )
        df = df[df["ticker"].isin(list(SELECTED_SECURITIES.keys()))]
        df["index_code"] = index
        dfs_index.append(df)

    return pd.concat(dfs_index, ignore_index=True)


def add_internal_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Из справочников акций и индексов (dwh.security/dwh.index) получает словари
    с отношенинем {акция/индекс : id}.
    Далее добавляет идентификаторы БД в основную таблицу.
    """
    index_id = get_index_ids(list(SELECTED_INDICES.keys()))
    security_id = get_security_ids(list(SELECTED_SECURITIES.keys()))

    df["index_id"] = df["index_code"].map(index_id)
    df["security_id"] = df["ticker"].map(security_id)

    if df["index_id"].isna().any():
        missing = df.loc[df["index_id"].isna(), "index_code"].unique().tolist()
        raise ValueError(f"Не найдены index_id для индексов: {missing}")

    if df["security_id"].isna().any():
        missing = df.loc[df["security_id"].isna(), "ticker"].unique().tolist()
        raise ValueError(f"Не найдены security_id для акций: {missing}")
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.index_composition."""
    df = df.rename(columns={"from": "date_from", "till": "date_till"})
    df = df[
        [
            "index_id",
            "security_id",
            "date_from",
            "date_till",
        ]
    ]

    df["index_id"] = df["index_id"].astype("Int64")
    df["security_id"] = df["security_id"].astype("Int64")
    df["date_from"] = pd.to_datetime(df["date_from"]).dt.date
    df["date_till"] = pd.to_datetime(df["date_till"]).dt.date
    return df


def dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса."""
    df = df.astype(object).where(pd.notna(df), None)
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        row = dict(zip(columns, values))
        rows.append(row)
    return rows


def load_index_composition() -> None:
    logger.info("Начата выгрузка данных для dwh.index_composition")
    df = get_moex_index_composition()
    if df.empty:
        logger.warning("Данные по сплиту/дроблению отсутствуют")
        return
    df = add_internal_ids(df)
    df = transform_data(df)

    rows = dataframe_to_rows(df)
    upsert_index_composition(rows)
    logger.info("загрузка dwh.index_composition завершена")


if __name__ == "__main__":
    setup_logging()
    load_index_composition()
