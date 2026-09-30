"""
ETL-процесс загрузки получения динамики котировок валют по ЦБ в dwh.currency_rate.

Получает данные www.cbr.ru по валютам из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging
from datetime import date
from io import BytesIO

import pandas as pd

from moex_analytics.api.cb import get_currency_rate
from moex_analytics.db.read import get_currency_rate_range
from moex_analytics.db.write import upsert_currency_rate
from moex_analytics.etl.common import calculate_missing_date_ranges, dataframe_to_rows
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import CBR_CURRENCIES, HISTORY_DATE_FROM, HISTORY_DATE_TO

logger = logging.getLogger(__name__)


COLUMNS_NAME = {
    # —	—	currency_id
    "Date": "rate_date",
    "Nominal": "nominal",
    "Value": "rate_value",
    "VunitRate": "unit_rate",
}


def get_load_ranges() -> list[tuple[str, int, date, date]]:
    """Для каждой валюты подготавливаются необходимые к выгрузке диапазоны дат.
    Диапазоны расcчитываются на основе периода:
        указанного в настройках проекта и уже загруженных в БД.
    На основе недостающих периодов и строится диапазон в формате:
    (
        Код валюты ЦБ,
        ID валюты в БД,
        дата начала периода,
        дата окончания периода
    )."""
    db_range = get_currency_rate_range(list(CBR_CURRENCIES.keys()))

    load_ranges: list[tuple[str, int, date, date]] = []

    for cbr_id, currency_data in db_range.items():
        ranges = calculate_missing_date_ranges(
            target_from=HISTORY_DATE_FROM,
            target_to=HISTORY_DATE_TO,
            loaded_from=currency_data["date_from"],
            loaded_to=currency_data["date_to"],
        )

        for date_from, date_to in ranges:
            load_ranges.append(
                (cbr_id, currency_data["currency_id"], date_from, date_to)
            )

    return load_ranges


def get_currency_data_range(ranges: list[tuple[str, int, date, date]]) -> pd.DataFrame:
    dfs_currency_ranges: list[pd.DataFrame] = []
    for load_range in ranges:
        cbr_id, currency_id, date_from, date_to = load_range
        params = {
            "VAL_NM_RQ": cbr_id,
            "date_req1": date_from.strftime("%d/%m/%Y"),
            "date_req2": date_to.strftime("%d/%m/%Y"),
        }
        data = get_currency_rate(params=params)
        df = pd.read_xml(
            BytesIO(data),
            xpath=".//Record",
            parser="etree",
            encoding="windows-1251",
        )
        df["currency_id"] = currency_id
        dfs_currency_ranges.append(df)

    return pd.concat(dfs_currency_ranges, ignore_index=True)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные ЦБ к структуре dwh.currency_rate."""
    df = df[["currency_id", *COLUMNS_NAME.keys()]]
    df = df.rename(columns=COLUMNS_NAME)

    df["currency_id"] = df["currency_id"].astype("Int64")
    df["nominal"] = df["nominal"].astype("Int64")
    df["rate_date"] = pd.to_datetime(df["rate_date"], format="%d.%m.%Y").dt.date
    df["rate_value"] = df["rate_value"].str.replace(",", ".", regex=False).astype(float)
    df["unit_rate"] = df["unit_rate"].str.replace(",", ".", regex=False).astype(float)
    return df


def load_currency_rate() -> None:
    logger.info("Начата выгрузка данных для dwh.currency_rate")
    load_ranges = get_load_ranges()
    if not load_ranges:
        logger.warning("Новых интервалов не обнаружено")
        return

    df = get_currency_data_range(load_ranges)
    if df.empty:
        logger.warning("Новых интервалов не обнаружено")
        return

    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_currency_rate(rows)
    logger.info("Загрузка dwh.currency_rate завершена")


if __name__ == "__main__":
    setup_logging()
    load_currency_rate()
