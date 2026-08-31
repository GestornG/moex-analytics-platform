"""
Операции записи данных ETL в PostgreSQL DWH.
"""

import logging

from moex_analytics.db.connection import get_connection

logger = logging.getLogger(__name__)

UPSERT_SECURITIES_SQL = """
    INSERT INTO dwh.security (
        secid,
        short_name,
        face_value,
        name,
        face_currency_code,
        issue_size,
        isin,
        latin_name,
        reg_number,
        currency_code,
        security_type_code,
        list_level,
        prev_date
    )
    VALUES (
        %(secid)s,
        %(short_name)s,
        %(face_value)s,
        %(name)s,
        %(face_currency_code)s,
        %(issue_size)s,
        %(isin)s,
        %(latin_name)s,
        %(reg_number)s,
        %(currency_code)s,
        %(security_type_code)s,
        %(list_level)s,
        %(prev_date)s

    )
    ON CONFLICT (secid)
    DO UPDATE SET
        short_name = EXCLUDED.short_name,
        face_value = EXCLUDED.face_value,
        name = EXCLUDED.name,
        face_currency_code = EXCLUDED.face_currency_code,
        issue_size = EXCLUDED.issue_size,
        isin = EXCLUDED.isin,
        latin_name = EXCLUDED.latin_name,
        reg_number = EXCLUDED.reg_number,
        currency_code = EXCLUDED.currency_code,
        security_type_code = EXCLUDED.security_type_code,
        list_level = EXCLUDED.list_level,
        prev_date = EXCLUDED.prev_date;
"""


UPSERT_INDICES_SQL = """
    INSERT INTO dwh.index(
        index_code,
        short_name,
        analytics_from,
        analytics_till
    )
    VALUES (
        %(index_code)s,
        %(short_name)s,
        %(analytics_from)s,
        %(analytics_till)s
    )
    ON CONFLICT (index_code)
    DO UPDATE SET
        short_name = EXCLUDED.short_name,
        analytics_from = EXCLUDED.analytics_from,
        analytics_till = EXCLUDED.analytics_till
"""


UPSERT_SECURITY_DAILY_SQL = """
    INSERT INTO dwh.security_daily (
        security_id,
        trade_date,
        num_trades,
        value,
        open,
        low,
        high,
        waprice,
        close,
        volume
    )
    VALUES (
        %(security_id)s,
        %(trade_date)s,
        %(num_trades)s,
        %(value)s,
        %(open)s,
        %(low)s,
        %(high)s,
        %(waprice)s,
        %(close)s,
        %(volume)s
    )
    ON CONFLICT (security_id, trade_date)
    DO UPDATE SET
        num_trades = EXCLUDED.num_trades,
        value = EXCLUDED.value,
        open = EXCLUDED.open,
        low = EXCLUDED.low,
        high = EXCLUDED.high,
        waprice = EXCLUDED.waprice,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume;
"""


def upsert_securities(rows: list[dict[str, object]]) -> None:
    """Добавляет новые акции и актуализирует существующие."""
    if not rows:
        return

    logger.debug("Начата запись в dwh.security")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_SECURITIES_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.security", len(rows))
    return


def upsert_index(rows: list[dict[str, object]]) -> None:
    if not rows:
        return

    logger.debug("Начата запись в dwh.index")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_INDICES_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.index", len(rows))
    return


def upsert_security_daily(rows: list[dict[str, object]]) -> None:
    """Добавляет и актуализирует дневную историю торгов акций."""
    if not rows:
        return

    logger.debug("Начата запись в dwh.security_daily")

    with (
        get_connection() as connection,
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            UPSERT_SECURITY_DAILY_SQL,
            rows,
        )

    logger.debug(
        "Записано %d строк в dwh.security_daily",
        len(rows),
    )
