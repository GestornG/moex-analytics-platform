"""
ETL-процесс создания справочника для единых временных разрезов,
группировки данных по периодам и контроля пропущенных дат в dwh.calendar.

Подготавливает плоскую таблицу, преобразует к модели DWH и передаёт
подготовленные данные в слой PostgreSQL.
"""

import logging
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from moex_analytics.db.write import upsert_calendar
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import HISTORY_DATE_FROM, HISTORY_DATE_TO

logger = logging.getLogger(__name__)


CALENDAR_DATE_FROM = date(2010, 1, 1)
CALENDAR_DATE_TO = date(2040, 12, 31)


def checking_calendar_periods() -> tuple[date, date] | None:
    """Проверяет необходимость расширить справочник dwh.calendar"""
    if CALENDAR_DATE_FROM <= HISTORY_DATE_FROM - relativedelta(
        years=5
    ) and CALENDAR_DATE_TO >= HISTORY_DATE_TO + relativedelta(years=5):
        return None

    date_from = min(
        CALENDAR_DATE_FROM,
        HISTORY_DATE_FROM - relativedelta(years=7),
    )
    date_to = max(
        CALENDAR_DATE_TO,
        HISTORY_DATE_TO + relativedelta(years=7),
    )

    return date_from, date_to


def get_dataframe_with_date(date_from: date, date_to: date) -> pd.DataFrame:
    """Создает заполенный pd.DataFrame для dwh.calendar."""
    df = pd.DataFrame({"calendar_date": pd.date_range(date_from, date_to)})
    df["period"] = df["calendar_date"].dt.strftime("%Y%m")
    df["year"] = df["calendar_date"].dt.year
    df["quarter"] = df["calendar_date"].dt.quarter
    df["month_name"] = df["calendar_date"].dt.month_name()
    df["month_num"] = df["calendar_date"].dt.month
    df["day_of_month"] = df["calendar_date"].dt.day
    df["day_of_week"] = df["calendar_date"].dt.dayofweek + 1
    df["day_of_week_name"] = df["calendar_date"].dt.day_name()
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные к структуре dwh.calendar."""
    df["calendar_date"] = pd.to_datetime(df["calendar_date"]).dt.date
    df["period"] = df["period"].astype("Int64")
    df["year"] = df["year"].astype("Int64")
    df["quarter"] = df["quarter"].astype("Int64")
    df["month_num"] = df["month_num"].astype("Int64")
    df["day_of_month"] = df["day_of_month"].astype("Int64")
    df["day_of_week"] = df["day_of_week"].astype("Int64")
    return df


def load_calendar() -> None:
    date_range = checking_calendar_periods()
    if date_range is None:
        logger.info("Текущий диапазон справочника dwh.calendar достаточен.")
        return

    logger.info("Начат процесс обновления dwh.calendar.")
    df = get_dataframe_with_date(*date_range)
    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_calendar(rows)
    logger.info("Завершен процесс обновления dwh.calendar.")


if __name__ == "__main__":
    setup_logging()
    load_calendar()
