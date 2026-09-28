"""
ETL-процесс загрузки справочника акций в dwh.security.

Получает справочные данные MOEX, ограничивает их scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging

import pandas as pd

from moex_analytics.api.moex import get_stock_security
from moex_analytics.api.tbank import find_instrument
from moex_analytics.db.write import upsert_securities
from moex_analytics.etl.common import dataframe_to_rows
from moex_analytics.logging_config import setup_logging
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


def get_tbank_uid(df: pd.DataFrame) -> pd.DataFrame:
    """Выгружает из api.tbank.ru технический id инструмента ТБанк "instrument_uid"
    и добавляет его в исходны dateframe."""
    uid_dict: dict[str, str] = {}
    for isin in df["ISIN"].unique():
        data = find_instrument(isin)
        instruments = data.get("instruments", [])

        matched_instrument = None
        for instrument in instruments:
            if instrument.get("isin") == isin:
                matched_instrument = instrument
                break

        if matched_instrument is None:
            logger.warning(
                "T-Invest инструмент не найден для ISIN=%s",
                isin,
            )
            continue

        uid_dict[isin] = matched_instrument["uid"]

    df["tbank_uid"] = df["ISIN"].map(uid_dict)
    return df


def transform_security_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные MOEX к структуре dwh.security."""
    df = df[[*list(SECURITY_COLUMN_MAP.keys()), "tbank_uid"]]
    df = df.rename(columns=SECURITY_COLUMN_MAP)

    df["issue_size"] = df["issue_size"].astype("Int64")
    df["list_level"] = df["list_level"].astype("Int64")
    df["prev_date"] = pd.to_datetime(df["prev_date"]).dt.date
    return df


def load_security(t_token_available: bool = True) -> None:
    """Загружает и актуализирует справочник акций в dwh.security."""
    logger.info("Начата загрузка справочника акций dwh.security")
    df = get_security_data(
        secids=set(SELECTED_SECURITIES),
        board=SECURITY_BOARD,
    )

    df["tbank_uid"] = None
    if t_token_available:
        df = get_tbank_uid(df)

    df = transform_security_data(df)
    rows = dataframe_to_rows(df)
    upsert_securities(rows)
    logger.info("Завершена загрузка справочника акций dwh.security")


if __name__ == "__main__":
    setup_logging()
    load_security()
