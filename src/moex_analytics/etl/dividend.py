"""
ETL-процесс загрузки дивидендных событий в dwh.dividend.

Получает данные по дивидендным событиям из sandbox-invest-public-api.tbank.ru,
преобразует к модели DWH и передаёт подготовленные данные в слой PostgreSQL.
"""

import logging
from decimal import Decimal

import pandas as pd

from moex_analytics.api.tbank import get_dividends
from moex_analytics.db.read import get_security_tbank_uids
from moex_analytics.db.write import upsert_dividend
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import (
    HISTORY_DATE_FROM,
    HISTORY_DATE_TO,
    SELECTED_SECURITIES,
)

logger = logging.getLogger(__name__)


def get_dividends_data() -> pd.DataFrame:
    from_ts = f"{HISTORY_DATE_FROM}T00:00:00Z"
    to_ts = f"{HISTORY_DATE_TO}T23:59:59Z"

    security_uids = get_security_tbank_uids(list(SELECTED_SECURITIES.keys()))
    rows: list[dict] = []
    for sec_id, t_uid in security_uids.items():
        data = get_dividends(instrument_uid=t_uid, date_from=from_ts, date_to=to_ts)
        if data["dividends"]:
            for dividend in data["dividends"]:
                if dividend.get("dividendType") == "Cancelled":
                    continue
                dividend_net = dividend["dividendNet"]

                amount = Decimal(dividend_net["units"]) + Decimal(
                    dividend_net["nano"]
                ) / Decimal(1_000_000_000)
                rows.append(
                    {
                        "security_id": sec_id,
                        "registry_close_date": dividend["recordDate"][:10],
                        "dividend_value": amount,
                        "currency_code": dividend_net["currency"].upper(),
                    }
                )
    df = pd.DataFrame(rows)
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные к структуре dwh.dividend."""
    df["security_id"] = df["security_id"].astype("Int64")
    df["registry_close_date"] = pd.to_datetime(df["registry_close_date"]).dt.date
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


def load_dividend() -> None:
    logger.info("Начата выгрузка данных для dwh.dividend")

    df = get_dividends_data()
    if df.empty:
        logger.info("По текущим параметрам дивиденды отсутствуют.")
        return

    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_dividend(rows)
    logger.info("загрузка dwh.dividend завершена")


if __name__ == "__main__":
    setup_logging()
    load_dividend()
