"""
ETL-процесс загрузки дневной истории акций в dwh.security_daily.

Получает данные торгов MOEX за день по выбранному списку торгов из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging
import time
from datetime import date, timedelta
from typing import Any

import pandas as pd

from moex_analytics.api.moex import get_available_date_range, get_security_daily_history
from moex_analytics.db.read import get_security_daily_date_range
from moex_analytics.db.write import upsert_security_daily
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import (
    HISTORY_DATE_FROM,
    HISTORY_DATE_TO,
    SECURITY_BOARD,
    SELECTED_SECURITIES,
)

logger = logging.getLogger(__name__)

COLUMNS_NAME = {
    "TRADEDATE": "trade_date",
    "NUMTRADES": "num_trades",
    "VALUE": "value",
    "OPEN": "open",
    "LOW": "low",
    "HIGH": "high",
    "WAPRICE": "waprice",
    "CLOSE": "close",
    "VOLUME": "volume",
}


def get_available_moex_date_range() -> dict[str, dict[str, Any]]:
    """Возвращает словарь акций с периодом, в котором доступны данные торгов за день."""
    dict_range: dict[str, dict[str, Any]] = {}
    for security in SELECTED_SECURITIES:
        data = get_available_date_range(security=security)
        dict_range[security] = dict(
            zip(data["dates"]["columns"], data["dates"]["data"][0])
        )
    return dict_range


def get_security_daily_load_ranges() -> list[tuple[int, str, date, date]]:
    """Для каждой акции подготавливаются необходимые к выгрузке диапазоны дат.
    Диапазоны расчитываются на основе периода:
        указанного в настройках проекта,
        достуного в данных ISS MOEX,
        уже загруженных в БД.
    На основе недостяющих периодов и строится диапазон в формате:
    (
        ID акции в БД,
        Краткое наименование акции,
        дата начала периода,
        дата окончания периода
    )."""

    db_rows = get_security_daily_date_range(list(SELECTED_SECURITIES))
    moex_dict = get_available_moex_date_range()

    logger.debug("Доступные интервалы в MOEX: %s", moex_dict)
    logger.debug("Интервалы из БД: %s", db_rows)

    load_ranges: list[tuple[int, str, date, date]] = []
    # list[(security_id, secid, min_date, max_date)]

    for row in db_rows:
        secid = row["secid"]
        security_id = row["security_id"]
        target_from = max(
            HISTORY_DATE_FROM, date.fromisoformat(moex_dict[secid]["from"])
        )
        target_to = min(HISTORY_DATE_TO, date.fromisoformat(moex_dict[secid]["till"]))

        if target_from > target_to:
            continue

        if row["min_date"] is None or row["max_date"] is None:
            load_ranges.append((security_id, secid, target_from, target_to))
            continue

        if row["min_date"] <= target_from and row["max_date"] >= target_to:
            continue

        if target_to < row["min_date"] or target_from > row["max_date"]:
            load_ranges.append((security_id, secid, target_from, target_to))
            continue

        if target_from < row["min_date"]:
            load_ranges.append(
                (security_id, secid, target_from, row["min_date"] - timedelta(days=1))
            )

        if target_to > row["max_date"]:
            load_ranges.append(
                (security_id, secid, row["max_date"] + timedelta(days=1), target_to)
            )
    return load_ranges


def get_security_daily_moex_data(
    load_ranges: list[tuple[int, str, date, date]],
) -> pd.DataFrame:
    """Выгружает за указанный период для каждой акции данные по торгам за день.
    Учтена пагинация для лимитированного количества строк в выгрузке.
    """
    dfs_range_security: list[pd.DataFrame] = []
    for security_id, secid, date_from, date_to in load_ranges:
        params = {
            "from": date.strftime(date_from, format="%Y-%m-%d"),
            "till": date.strftime(date_to, format="%Y-%m-%d"),
            "tradingsession": 3,
            "start": 0,
        }
        while True:
            response = get_security_daily_history(
                board=SECURITY_BOARD, security=secid, params=params
            )
            cursor = dict(
                zip(
                    response["history.cursor"]["columns"],
                    response["history.cursor"]["data"][0],
                )
            )

            df = pd.DataFrame(
                columns=response["history"]["columns"], data=response["history"]["data"]
            )
            df["security_id"] = security_id
            dfs_range_security.append(df)

            logger.debug(
                "Выгружено %d строк из %d по акции %s",
                min(
                    cursor["INDEX"] + len(response["history"]["data"]), cursor["TOTAL"]
                ),
                cursor["TOTAL"],
                secid,
            )

            if cursor["INDEX"] + cursor["PAGESIZE"] >= cursor["TOTAL"]:
                break

            params["start"] += cursor["PAGESIZE"]
            time.sleep(0.2)

    if not dfs_range_security:
        return pd.DataFrame()

    return pd.concat(dfs_range_security, ignore_index=True)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.security_daily."""
    df = df[["security_id", *COLUMNS_NAME.keys()]]
    df = df.rename(columns=COLUMNS_NAME)

    df["security_id"] = df["security_id"].astype("Int64")
    df["num_trades"] = df["num_trades"].astype("Int64")
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    df = df.astype(object).where(pd.notna(df), None)
    return df


def dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса."""
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        row = dict(zip(columns, values))
        rows.append(row)
    return rows


def load_security_daily() -> None:
    logger.info("Начата выгрузка данных для dwh.security_daily")
    securities_list = get_security_daily_load_ranges()

    if not securities_list:
        logger.info("Новых интервалов не обнаружено")
        return
    else:
        logger.info(
            "Получен список акций и диапазонов для загрузки: %s", securities_list
        )

    df = get_security_daily_moex_data(securities_list)
    if df.empty:
        logger.info("Данные по рассчитанным диапазонам отсутствуют")
        return

    logger.info("Получены данные по дневным торгам")
    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_security_daily(rows)
    logger.info("Выгрузка данных для dwh.security_daily завершена")


if __name__ == "__main__":
    setup_logging()
    load_security_daily()
