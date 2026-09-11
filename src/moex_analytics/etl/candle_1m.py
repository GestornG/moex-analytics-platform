"""
ETL-процесс загрузки минутных свечей акций и индексов в dwh.candle_1m

Получает данные торгов MOEX за одну минуту работы по списку акций и ндексов получаемых
из scope проекта. Преобразует к модели DWH и передаёт подготовленные данные в
слой PostgreSQL.
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from moex_analytics.api.moex import get_available_candle_range, get_candle_1м
from moex_analytics.db.read import get_candle_1m_range
from moex_analytics.db.write import upsert_candle_1m
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import (
    HISTORY_DATE_FROM,
    HISTORY_DATE_TO,
    SECURITY_BOARD,
    SELECTED_INDICES,
    SELECTED_SECURITIES,
)

logger = logging.getLogger(__name__)


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


def get_candle_interval(response: dict[str, Any]) -> tuple:
    """Из диапазонов доступности свечей MOEX ISS вычленяет начало и
    конец для минутного интервала.
    Возвращает:
        Кортеж (начало, конец)"""
    columns = response["borders"]["columns"]
    interval_idx = columns.index("interval")

    begin, end, _ = next(
        row for row in response["borders"]["data"] if row[interval_idx] == 1
    )
    return begin, end


def get_available_moex_range():
    """Из MOEX ISS по акции/индексу получает доступные интервалы для свечей.
    Возвращает:
        Словарь доступности минутных свечей: {акция/индекс: (начало, конец),}
    """
    available_range: dict[str, tuple] = {}

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
    """Расчитывает интервалы дат, за которые нужно догрузить информацию по свечам для
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
        ranges.append((target_from, date_min - timedelta(days=1)))

    if target_to > date_max:
        ranges.append((date_max + timedelta(days=1), target_to))
    return ranges


def get_candle_loading_interval() -> list[tuple[str, int, str, date, date]]:
    """На основе данных хранящихся в БД, периодом заданным проектом и доступными
    данными по свечам_1м в moex iss рассчитываются для каждого инструмента периоды
    для которых необходимо догрузить данные.
    Возвращает:
        Список кортежей для выгрузки свеч по индексам и акциям в формате:
        list[(type, id, name, min_date, max_date)].
    """
    moex_range = get_available_moex_range()
    db_rows = get_candle_1m_range(
        list(SELECTED_INDICES.keys()), list(SELECTED_SECURITIES.keys())
    )

    loading_instrument_range: list[tuple[str, int, str, date, date]] = []
    # list[(type, id, name, min_date, max_date)]

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


def download_with_pagiantion(
    board: str, inst_name: str, market: str, date_from: date, date_to: date
) -> pd.DataFrame:
    """
    Для каждого инструмента формирует цикл выгрузки минутных свечей по итервалу.
    Пагинация обрабатыватывается по количеству выгруженных строк, до тех пор,
    пока данные не перестанут выгружаться (api вернет 0 строк данных).
    Возвращает:
        Таблицу (pd.DataFrame) с минутными свечами по инструменты + инервалу.
        Если данных нет, то pd.DataFrame пустой.
    """

    params = {
        "interval": 1,
        "from": date.strftime(date_from, format="%Y-%m-%d"),
        "till": date.strftime(date_to, format="%Y-%m-%d"),
        "start": 0,
    }

    dfs_list: list[pd.DataFrame] = []
    while True:
        response = get_candle_1м(
            market=market, board=board, security=inst_name, params=params
        )

        rows_count = response["candles"]["data"]
        if not rows_count:
            break

        df = pd.DataFrame(
            columns=response["candles"]["columns"], data=response["candles"]["data"]
        )

        dfs_list.append(df)

        params["start"] += len(rows_count)
        time.sleep(0.3)

    if not dfs_list:
        return pd.DataFrame()

    return pd.concat(dfs_list, ignore_index=True)


def get_candle_moex_data(
    instrument_range: list[tuple[str, int, str, date, date]],
) -> pd.DataFrame:
    """Готовит, передает параметры для выгрузки минутных свечей для акций и индексов.
    Получает pd.DateFrame минутных свечей по каждому инструменты за указанный период.
    Возвращает:
    Общий pd.DateFrame минутных свечей по всем инструментам.
    """
    dfs_candles: list[pd.DataFrame] = []
    for row in instrument_range:
        inst_type, inst_id, inst_name, date_from, date_to = row

        if inst_type == "index":
            instrument_df = download_with_pagiantion(
                board=SELECTED_INDICES[inst_name]["board"],
                inst_name=inst_name,
                market="index",
                date_from=date_from,
                date_to=date_to,
            )
            if instrument_df.empty:
                continue

            instrument_df["index_id"] = inst_id
            instrument_df["security_id"] = None

        else:
            instrument_df = download_with_pagiantion(
                board=SECURITY_BOARD,
                inst_name=inst_name,
                market="shares",
                date_from=date_from,
                date_to=date_to,
            )
            if instrument_df.empty:
                continue

            instrument_df["security_id"] = inst_id
            instrument_df["index_id"] = None

        dfs_candles.append(instrument_df)

    if not dfs_candles:
        return pd.DataFrame()

    return pd.concat(dfs_candles, ignore_index=True)


def transfor_date(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.candle_1m."""
    df = df[["index_id", "security_id"] + list(COLUMNS_NAME.keys())]
    df = df.rename(columns=COLUMNS_NAME)

    df["security_id"] = df["security_id"].astype("Int64")
    df["index_id"] = df["index_id"].astype("Int64")
    df["begin_ts"] = pd.to_datetime(df["begin_ts"])
    df["end_ts"] = pd.to_datetime(df["end_ts"])

    df = df.astype(object).where(pd.notna(df), None)
    return df


def dataframe_to_rows(
    df: pd.DataFrame,
) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса."""
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        row = dict(zip(columns, values))
        rows.append(row)
    return rows


def separation_dataframe(
    df: pd.DataFrame,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    """Разделяет данные на два массива по акциям и индексам для отдельной
    загрузки в БД.
    Возвращает:
        Два массива строк для по каждой групе, если данных по группе нет - None"""
    index: list[dict[str, object]]
    security: list[dict[str, object]]

    df_index = df[df["index_id"].notnull()].copy()
    df_security = df[df["security_id"].notnull()].copy()

    index = dataframe_to_rows(df_index)
    security = dataframe_to_rows(df_security)

    logger.info("К загрузке %d строк по минутным свечам индексов", len(index))
    logger.info("К загрузке %d строк по минутным свечам акций", len(security))
    return index, security


def load_candle_1m() -> None:
    logger.info("Начата выгрузка данных для dwh.candle_1m")

    loading_interval = get_candle_loading_interval()
    if not loading_interval:
        logger.info("Новых интервалов не обнаружено")
        return
    else:
        logger.info(
            "Получен список инструментов и диапазонов для загрузки: %s",
            loading_interval,
        )

    df = get_candle_moex_data(loading_interval)
    if df.empty:
        logger.info("Данные по рассчитанным диапазонам отсутствуют")
        return

    df = transfor_date(df)

    index, security = separation_dataframe(df)
    upsert_candle_1m(index, security)
    return


if __name__ == "__main__":
    setup_logging()
    load_candle_1m()
