"""
ETL-процесс загрузки дневной истории индексов в dwh.index_daily.

Получает данные торгов MOEX за день по выбранному списку индексов из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging
import time
from datetime import date, timedelta

import pandas as pd

from moex_analytics.api.moex import get_index_daily_history
from moex_analytics.db.read import get_index_available_range, get_index_daily_date_range
from moex_analytics.db.write import upsert_index_daily
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import HISTORY_DATE_FROM, HISTORY_DATE_TO, SELECTED_INDICES

logger = logging.getLogger(__name__)

COLUMNS_NAME = {
    "BOARDID": "board_code",
    "TRADEDATE": "trade_date",
    "CLOSE": "close",
    "OPEN": "open",
    "HIGH": "high",
    "LOW": "low",
    "CAPITALIZATION": "capitalization",
    "DIVISOR": "divisor",
}


def get_index_daily_load_ranges() -> list[tuple[int, str, date, date]]:
    """Для каждого индекса подготавливаются необходимые к выгрузке диапазоны дат.
    Диапазоны рассчитываются на основе периода:
        указанного в настройках проекта,
        доступного в данных ISS MOEX, уже загруженных в dwh.index,
        уже загруженных в БД данных по дням.
    На основе недостяющих периодов и строится диапазон в формате:
    (
        ID индекса в БД,
        Краткое наименование индекса,
        дата начала периода выгрузки,
        дата окончания периода выгрузки
    )."""

    db_index = get_index_available_range(list(SELECTED_INDICES))
    db_rows = get_index_daily_date_range(list(db_index.keys()))
    logger.debug("Данные по справочнику Индексов из БД: %s", db_index)
    logger.debug("Интервалы из dwh.index_daily: %s", db_rows)

    load_ranges: list[tuple[int, str, date, date]] = []
    for row in db_rows:
        index_id = row["index_id"]
        index_code = db_index[index_id]["index_code"]
        target_from = max(HISTORY_DATE_FROM, db_index[index_id]["analytics_from"])
        target_to = min(HISTORY_DATE_TO, db_index[index_id]["analytics_till"])

        if target_from > target_to:
            continue

        if row["min_date"] is None or row["max_date"] is None:
            load_ranges.append((index_id, index_code, target_from, target_to))
            continue

        if row["min_date"] <= target_from and row["max_date"] >= target_to:
            continue

        if target_to < row["min_date"] or target_from > row["max_date"]:
            load_ranges.append((index_id, index_code, target_from, target_to))
            continue

        if target_from < row["min_date"]:
            load_ranges.append(
                (
                    index_id,
                    index_code,
                    target_from,
                    row["min_date"] - timedelta(days=1),
                )
            )

        if target_to > row["max_date"]:
            load_ranges.append(
                (
                    index_id,
                    index_code,
                    row["max_date"] + timedelta(days=1),
                    target_to,
                )
            )
    return load_ranges


def get_index_daily_moex_data(
    load_ranges: list[tuple[int, str, date, date]],
) -> pd.DataFrame:
    """Выгружает за указанный период для каждого индекса данные по торгам за день.
    Учтена пагинация для лимитированного количества строк в выгрузке.
    """
    dfs_range_index: list[pd.DataFrame] = []
    for index_id, index, date_from, date_to in load_ranges:
        params = {
            "from": date.strftime(date_from, format="%Y-%m-%d"),
            "till": date.strftime(date_to, format="%Y-%m-%d"),
            "tradingsession": 3,
            "start": 0,
        }
        print(
            f"index={index}, board={SELECTED_INDICES[index]['board']}, params={params}"
        )
        while True:
            response = get_index_daily_history(
                index=index, board=SELECTED_INDICES[index]["board"], params=params
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
            df["index_id"] = index_id
            dfs_range_index.append(df)

            logger.debug(
                "Выгружено %d строк из %d по индексу %s",
                min(
                    cursor["INDEX"] + len(response["history"]["data"]), cursor["TOTAL"]
                ),
                cursor["TOTAL"],
                index,
            )

            if cursor["INDEX"] + cursor["PAGESIZE"] >= cursor["TOTAL"]:
                break

            params["start"] += cursor["PAGESIZE"]
            time.sleep(0.2)

    return pd.concat(dfs_range_index, ignore_index=True)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.index_daily."""
    df = df[["index_id", *COLUMNS_NAME.keys()]]
    df = df.rename(columns=COLUMNS_NAME)

    df["index_id"] = df["index_id"].astype("Int64")
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


def load_index_daily() -> None:
    logger.info("Начата выгрузка данных для dwh.index_daily")
    indices_list = get_index_daily_load_ranges()

    if not indices_list:
        logger.info("Новых интервалов не обнаружено")
        return

    logger.info("Получен список индексов и диапазонов для загрузки: %s", indices_list)

    df = get_index_daily_moex_data(indices_list)
    logger.info("Получены данные по дневным торгам")
    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_index_daily(rows)
    logger.info("Выгрузка данных для dwh.index_daily завершена")


if __name__ == "__main__":
    setup_logging()
    load_index_daily()
