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


INDEX_CATALOGUE = """
SELECT
    index_id,
    index_code,
    analytics_from,
    analytics_till
FROM dwh.index
WHERE index_code = ANY(%s)
"""


INDEX_DAILY_RANGE = """
SELECT
    i.index_id,
    MIN(id.trade_date) AS min_date,
    MAX(id.trade_date) AS max_date
FROM dwh.index AS i
LEFT JOIN dwh.index_daily AS id
    ON id.index_id = i.index_id
WHERE i.index_id = ANY(%s)
GROUP BY
    i.index_id
"""


CANDLE_1M_RANGE = """
WITH candle_range AS (
    SELECT
        index_id,
        security_id,
        MIN(begin_ts)::date AS min_date,
        MAX(begin_ts)::date AS max_date
    FROM dwh.candle_1m
    GROUP BY
        index_id,
        security_id
)

SELECT
    'index' as instrument_type,
    i.index_id as instrument_id,
    i.index_code as instrument_name,
    c.min_date,
    c.max_date
FROM dwh.index AS i
LEFT JOIN candle_range AS c
    ON i.index_id = c.index_id
WHERE i.index_code = ANY(%s)

UNION ALL

SELECT
    'security' as instrument_type,
    s.security_id as instrument_id,
    s.secid as instrument_name,
    c.min_date,
    c.max_date
FROM dwh.security AS s
LEFT JOIN candle_range AS c
    ON s.security_id = c.security_id
WHERE s.secid = ANY(%s);
"""


SECURITY_IDS = """
SELECT
    secid,
    security_id
FROM dwh.security
WHERE
    secid = ANY(%s)
"""


def get_securitys_from_db():
    """Возвращает перечень уникальных наименований акций из таблицы dwh.security."""
    with get_connection() as connection:
        rows = connection.execute("SELECT DISTINCT(secid) FROM dwh.security").fetchall()
    return {secid for (secid,) in rows}


def get_security_daily_date_range(security: list[str]) -> list[dict[str, Any]]:
    """Возвращает перечень акций по списку и указывает диапазон имеющихся в БД дат."""
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


def get_index_available_range(
    index: list[str],
) -> dict[int, dict[str, Any]]:
    """Возвращает перечень индексов по списку из справочника индексов
    с доступным для выгрузки диапазоном.
    """
    if not index:
        return {}

    with (
        get_connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        rows = cursor.execute(
            INDEX_CATALOGUE,
            (index,),
        ).fetchall()

    return {row["index_id"]: row for row in rows}


def get_index_daily_date_range(index_id: list[int]) -> list[dict[str, Any]]:
    """Возвращает перечень индексов по списку с диапазоном имеющихся в БД дат."""
    if not index_id:
        return []

    with (
        get_connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        rows = cursor.execute(
            INDEX_DAILY_RANGE,
            (index_id,),
        ).fetchall()
    return rows


def get_candle_1m_range(index: list[str], security: list[str]) -> list[dict[str, Any]]:
    """
    Из таблицы dwh.candle_1m по заданному списку выгружает пару минимальное и
    максимальное время свечей в таблице для каждого индекса/акции.
    """

    if not index and not security:
        return []

    with (
        get_connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        rows = cursor.execute(
            CANDLE_1M_RANGE,
            (index, security),
        ).fetchall()

    return rows


def get_security_ids(securities: list[str]) -> dict[str, int]:
    """Возвращает соответствие secid → security_id."""
    if not securities:
        return {}

    with (
        get_connection() as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        rows = cursor.execute(
            SECURITY_IDS,
            (securities,),
        ).fetchall()

    return {row["secid"]: row["security_id"] for row in rows}
