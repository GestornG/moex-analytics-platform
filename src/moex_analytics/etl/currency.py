"""
ETL-процесс загрузки справочника по кодам валют ЦБ dwh.currency .

Получает данные www.cbr.ru по валютам из scope проекта,
преобразует к модели DWH и передаёт подготовленные данные
в слой PostgreSQL.
"""

import logging
from io import BytesIO

import pandas as pd

from moex_analytics.api.cb import get_currency_cb
from moex_analytics.db.write import upsert_currency
from moex_analytics.logging_config import setup_logging
from moex_analytics.settings import CBR_CURRENCIES

logger = logging.getLogger(__name__)

COLUMNS_CURRENCY = {
    "ID": "cbr_id",
    "Name": "name",
    "EngName": "eng_name",
    "Nominal": "nominal",
    "ISO_Num_Code": "iso_num_code",
    "ISO_Char_Code": "iso_char_code",
}


def get_currency_data() -> pd.DataFrame:
    """Получает справочник валют ЦБ РФ.
    Ограничивает перечнем из scope проекта.
    Дополнительная проверка на соответствие ID и ISO_Char_Code.
    Возвращает:
        pd.DataFrame с необходимой валютой.
    """
    data = get_currency_cb()

    df = pd.read_xml(
        BytesIO(data),
        xpath=".//Item",
        parser="etree",
        encoding="windows-1251",
    )

    df = df[df["ID"].isin(CBR_CURRENCIES.keys())]

    catalog = dict(zip(df["ID"], df["ISO_Char_Code"]))
    for currency_id, currency_code in CBR_CURRENCIES.items():
        code = catalog.get(currency_id)
        if code != currency_code:
            raise ValueError(
                f"Несоответствие валюты {currency_id}."
                f"Ожидается: {currency_code}, пришло: {code}"
            )
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует данные ЦБ к структуре dwh.currency."""
    df = df[COLUMNS_CURRENCY.keys()]
    df = df.rename(columns=COLUMNS_CURRENCY)

    df["nominal"] = df["nominal"].astype("Int64")
    df["iso_num_code"] = df["iso_num_code"].astype("Int64")
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


def load_currency() -> None:
    logger.info("Начата выгрузка данных для dwh.currency")
    df = get_currency_data()

    df = transform_data(df)
    rows = dataframe_to_rows(df)
    upsert_currency(rows)
    logger.info("Загрузка dwh.currency завершена")


if __name__ == "__main__":
    setup_logging()
    load_currency()
