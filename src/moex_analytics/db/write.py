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
        list_level
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
        %(list_level)s
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
        list_level = EXCLUDED.list_level;
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
