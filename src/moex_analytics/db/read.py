from typing import Any

from psycopg.rows import dict_row

from moex_analytics.db.connection import get_connection

SECURITY_DAILY_RANGE = """
SELECT
    s.security_id,
    s.secid,
    MIN(sd.trade_date) AS min_date,
    MAX(sd.trade_date) AS max_date
FROM dwh.security AS s
LEFT JOIN dwh.security_daily AS sd
    ON sd.security_id = s.security_id
WHERE s.secid = ANY(%s)
GROUP BY
    s.security_id,
    s.secid
"""


def get_securitys_from_db():
    """Возвращает перечень уникальных наименований акций из таблицы dwh.security."""
    with get_connection() as connection:
        rows = connection.execute("SELECT DISTINCT(secid) FROM dwh.security").fetchall()
    return {secid for (secid,) in rows}


def get_security_daily_date_range(security: list[str]) -> list[dict[str, Any]]:
    """Возвращает перечень акций по списку и указывает диапазон дат."""
    if not security:
        return []

    with (
        get_connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        rows = cursor.execute(
            SECURITY_DAILY_RANGE,
            (security,),
        ).fetchall()
    return rows
