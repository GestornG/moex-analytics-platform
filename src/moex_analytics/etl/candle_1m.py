"""
ETL-процесс загрузки минутных свечей акций и индексов в dwh.candle_1m

Получает данные торгов MOEX за одну минуту работы по списку акций и индексов получаемых
из scope проекта. Преобразует к модели DWH и передаёт подготовленные данные в
слой PostgreSQL.
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from moex_analytics.api.moex import get_available_candle_range, get_candle_1m
from moex_analytics.db.read import get_candle_1m_range
from moex_analytics.db.write import upsert_candle_1m
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import (
    HISTORY_DATE_FROM,
    HISTORY_DATE_TO,
    SECURITY_BOARD,
    SELECTED_INDICES,
    SELECTED_SECURITIES,
)

logger = logging.getLogger(__name__)

type CandleLoadingRange = tuple[
    str,  # instrument_type
    int,  # instrument_id
    str,  # instrument_name
    date,  # date_from
    date,  # date_to
]

COLUMNS_NAME = {
    "begin": "begin_ts",
    "end": "end_ts",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "value": "value",
    "volume": "volume",
}

CANDLE_CHUNK_DAYS = 30


def get_candle_interval(response: dict[str, Any]) -> tuple:
    """Из диапазонов доступности свечей MOEX ISS вычленяет начало и
    конец для минутного интервала.
    Возвращает:
        Кортеж (начало, конец)"""
    columns = response["borders"]["columns"]
    begin_idx = columns.index("begin")
    end_idx = columns.index("end")
    interval_idx = columns.index("interval")

    row = next(row for row in response["borders"]["data"] if row[interval_idx] == 1)

    return row[begin_idx], row[end_idx]


def get_available_moex_range():
    """Из MOEX ISS по акции/индексу получает доступные интервалы для свечей.
    Возвращает:
        Словарь доступности минутных свечей: {акция/индекс: (начало, конец),}
    """
    available_range: dict[str, Any] = {}

    for security in list(SELECTED_SECURITIES.keys()):
        response = get_available_candle_range(
            board=SECURITY_BOARD,
            security=security,
            market="shares",
        )
        available_range[security] = get_candle_interval(response)

    for index in SELECTED_INDICES:
        response = get_available_candle_range(
            board=SELECTED_INDICES[index]["board"],
            security=index,
            market="index",
        )
        available_range[index] = get_candle_interval(response)

    return available_range


def calculate_missing_ranges(
    target_from: date, target_to: date, date_min: date | None, date_max: date | None
) -> list[tuple[date, date]]:
    """Рассчитывает интервалы дат, за которые нужно догрузить информацию по свечам для
    каждой акции/индекса
    Возвращает:
        Список с кортежами, где кортеж содержит дату начала и дату
        конца рассчитаных интервалов.
    """
    ranges: list[tuple[date, date]] = []

    if target_from > target_to:
        return ranges

    if date_min is None or date_max is None:
        return [(target_from, target_to)]

    if date_min <= target_from and date_max >= target_to:
        return ranges

    if target_to < date_min or target_from > date_max:
        return [(target_from, target_to)]

    if target_from < date_min:
        ranges.append((target_from, date_min))

    if target_to > date_max:
        ranges.append((date_max, target_to))
    return ranges


def get_candle_loading_interval() -> list[CandleLoadingRange]:
    """На основе данных хранящихся в БД, периодом, заданным проектом и доступными
    данными по свечам_1м в MOEX ISS рассчитываются для каждого инструмента периоды
    для которых необходимо догрузить данные.
    Возвращает:
        Список кортежей для выгрузки свечей по индексам и акциям в формате:
        list[(type, id, name, min_date, max_date)].
    """
    moex_range = get_available_moex_range()
    db_rows = get_candle_1m_range(
        list(SELECTED_INDICES.keys()), list(SELECTED_SECURITIES.keys())
    )

    loading_instrument_range: list[CandleLoadingRange] = []
    # list[(type_instr, id, name, min_date, max_date)]

    for row in db_rows:
        name = row["instrument_name"]
        moex_from, moex_to = moex_range[name]
        target_from = max(HISTORY_DATE_FROM, datetime.fromisoformat(moex_from).date())
        target_to = min(HISTORY_DATE_TO, datetime.fromisoformat(moex_to).date())

        ranges = calculate_missing_ranges(
            target_from, target_to, row["min_date"], row["max_date"]
        )
        for date_from, date_to in ranges:
            loading_instrument_range.append(
                (
                    row["instrument_type"],
                    row["instrument_id"],
                    row["instrument_name"],
                    date_from,
                    date_to,
                )
            )

    return loading_instrument_range


def download_with_pagination(
    board: str, inst_name: str, market: str, date_from: date, date_to: date
) -> pd.DataFrame:
    """
    Для каждого инструмента формирует цикл выгрузки минутных свечей по интервалу.
    Пагинация обрабатывается по количеству выгруженных строк, до тех пор,
    пока данные не перестанут выгружаться (api вернет 0 строк данных).
    Возвращает:
        Таблицу (pd.DataFrame) с минутными свечами по инструменты + инервалу.
        Если данных нет, то pd.DataFrame пустой.
    """

    params = {
        "interval": 1,
        "from": date_from.strftime(format="%Y-%m-%d"),
        "till": date_to.strftime(format="%Y-%m-%d"),
        "start": 0,
    }

    dfs_list: list[pd.DataFrame] = []
    while True:
        response = get_candle_1m(
            market=market, board=board, security=inst_name, params=params
        )

        rows = response["candles"]["data"]
        if not rows:
            break

        df = pd.DataFrame(
            columns=response["candles"]["columns"], data=response["candles"]["data"]
        )

        dfs_list.append(df)

        params["start"] += len(rows)
        time.sleep(0.2)

    if not dfs_list:
        return pd.DataFrame()

    return pd.concat(dfs_list, ignore_index=True)


def get_candle_loading_chunks(
    loading_ranges: list[CandleLoadingRange],
    chunk_days: int,
) -> list[CandleLoadingRange]:
    """Для каждого "инструмент + диапазон" разбивает загрузки свечей на чанки по датам.
    Возвращает:
        Список кортежей по инструментам с разбитыми диапазонами."""
    if chunk_days <= 0:
        raise ValueError("chunk_days должен быть больше 0")

    loading_chunks = []

    for (
        instrument_type,
        instrument_id,
        instrument_name,
        date_from,
        date_to,
    ) in loading_ranges:
        chunk_from = date_from

        while chunk_from <= date_to:
            chunk_to = min(
                chunk_from + timedelta(days=chunk_days - 1),
                date_to,
            )

            loading_chunks.append(
                (
                    instrument_type,
                    instrument_id,
                    instrument_name,
                    chunk_from,
                    chunk_to,
                )
            )

            chunk_from = chunk_to + timedelta(days=1)

    return loading_chunks


def get_candle_moex_data(
    row: CandleLoadingRange,
) -> pd.DataFrame:
    """Готовит, передает параметры для выгрузки минутных свечей для акций и индексов.
    Получает pd.DataFrame минутных свечей по инструменту за указанный период.
    Возвращает:
        Общий pd.DataFrame минутных свечей.
    """

    inst_type, inst_id, inst_name, date_from, date_to = row

    if inst_type == "index":
        board = SELECTED_INDICES[inst_name]["board"]
        market = "index"
    elif inst_type == "security":
        board = SECURITY_BOARD
        market = "shares"
    else:
        raise ValueError(f"Unknown instrument type: {inst_type}")

    instrument_df = download_with_pagination(
        board=board,
        inst_name=inst_name,
        market=market,
        date_from=date_from,
        date_to=date_to,
    )

    if instrument_df.empty:
        return pd.DataFrame()

    if inst_type == "index":
        instrument_df["index_id"] = inst_id
        instrument_df["security_id"] = None
    else:
        instrument_df["security_id"] = inst_id
        instrument_df["index_id"] = None

    return instrument_df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.candle_1m."""
    df = df[["index_id", "security_id"] + list(COLUMNS_NAME.keys())]
    df = df.rename(columns=COLUMNS_NAME)

    df["security_id"] = df["security_id"].astype("Int64")
    df["index_id"] = df["index_id"].astype("Int64")
    df["begin_ts"] = pd.to_datetime(df["begin_ts"])
    df["end_ts"] = pd.to_datetime(df["end_ts"])
    return df


def load_candle_1m() -> None:
    logger.info("Начата выгрузка данных для dwh.candle_1m")

    loading_interval = get_candle_loading_interval()
    if not loading_interval:
        logger.info("Новых интервалов не обнаружено")
        return

    logger.info(
        "Рассчитано %d диапазонов загрузки",
        len(loading_interval),
    )
    logger.debug("Диапазоны загрузки: %s", loading_interval)

    loading_chunks = get_candle_loading_chunks(loading_interval, CANDLE_CHUNK_DAYS)

    for chunk in loading_chunks:
        inst_type, _, inst_name, date_from, date_to = chunk

        logger.info(
            "Загрузка %s: %s — %s",
            inst_name,
            date_from,
            date_to,
        )
        df = get_candle_moex_data(chunk)
        if df.empty:
            logger.info(
                "Данные отсутствуют: %s, %s — %s",
                inst_name,
                date_from,
                date_to,
            )
            continue

        df = transform_data(df)
        rows = dataframe_to_rows(df)
        upsert_candle_1m(rows, inst_type)
        logger.info(
            "Загружено %d свечей: %s, %s — %s",
            len(rows),
            inst_name,
            date_from,
            date_to,
        )


if __name__ == "__main__":
    setup_logging()
    load_candle_1m()
    logger.info("Загрузка dwh.candle_1m завершена")
