"""
ETL-процесс загрузки справочника акций в dwh.security.

Получает справочные данные MOEX, ограничивает их scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_stock_security
from moex_analytics.db.write import upsert_securities
from moex_analytics.settings import SECURITY_BOARD, SELECTED_SECURITIES

logger = logging.getLogger(__name__)

SECURITY_COLUMN_MAP = {
    "SECID": "secid",
    "SHORTNAME": "short_name",
    "FACEVALUE": "face_value",
    "SECNAME": "name",
    "FACEUNIT": "face_currency_code",
    "ISSUESIZE": "issue_size",
    "ISIN": "isin",
    "LATNAME": "latin_name",
    "REGNUMBER": "reg_number",
    "CURRENCYID": "currency_code",
    "SECTYPE": "security_type_code",
    "LISTLEVEL": "list_level",
    "PREVDATE": "prev_date",
}


def get_security_data(secids: set, board: str) -> pd.DataFrame:
    """Возвращает в табличном виде справочник акций из MOEX ISS."""
    data = get_stock_security(board=board)
    df = pd.DataFrame(
        columns=data["securities"]["columns"], data=data["securities"]["data"]
    )
    df = df[df["SECID"].isin(secids)]
    return df


def transform_security_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.security."""
    df = df[list(SECURITY_COLUMN_MAP.keys())]
    df = df.rename(columns=SECURITY_COLUMN_MAP)

    df["issue_size"] = df["issue_size"].astype("Int64")
    df["list_level"] = df["list_level"].astype("Int64")
    df["prev_date"] = pd.to_datetime(df["prev_date"]).dt.date
    return df


def dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса."""
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        row = dict(zip(columns, values))
        rows.append(row)
    return rows


def load_security() -> None:
    """Загружает и актуализирует справочник акций в dwh.security."""
    logger.info("Начата загрузка справочника акций dwh.security")
    df = get_security_data(
        secids=set(SELECTED_SECURITIES),
        board=SECURITY_BOARD,
    )
    df = transform_security_data(df)
    df = df.astype(object).where(pd.notna(df), None)
    rows = dataframe_to_rows(df)
    upsert_securities(rows)
    logger.info("Завершена загрузка справочника акций dwh.security")


if __name__ == "__main__":
    load_security()
