"""
Операции записи данных ETL в PostgreSQL DWH.
"""

import logging

from moex_analytics.db.connection import get_connection

logger = logging.getLogger(__name__)

UPSERT_SECURITIES_SQL = """
    INSERT INTO dwh.security as s (
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
        prev_date,
        tbank_uid
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
        %(prev_date)s,
        %(tbank_uid)s

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
        prev_date = EXCLUDED.prev_date,
        tbank_uid = COALESCE(EXCLUDED.tbank_uid, s.tbank_uid);
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


UPSERT_INDEX_DAILY_SQL = """
    INSERT INTO dwh.index_daily (
        index_id,
        board_code,
        trade_date,
        close,
        open,
        high,
        low,
        capitalization,
        divisor
    )
    VALUES (
        %(index_id)s,
        %(board_code)s,
        %(trade_date)s,
        %(close)s,
        %(open)s,
        %(high)s,
        %(low)s,
        %(capitalization)s,
        %(divisor)s
    )
    ON CONFLICT (index_id, trade_date)
    DO UPDATE SET
        board_code = EXCLUDED.board_code,
        close = EXCLUDED.close,
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        capitalization = EXCLUDED.capitalization,
        divisor = EXCLUDED.divisor;
"""


UPSERT_INDEX_CANDLE_1M_SQL = """
    INSERT INTO dwh.candle_1m (
        index_id,
        security_id,
        begin_ts,
        end_ts,
        open,
        close,
        high,
        low,
        value,
        volume
    )
    VALUES (
        %(index_id)s,
        %(security_id)s,
        %(begin_ts)s,
        %(end_ts)s,
        %(open)s,
        %(close)s,
        %(high)s,
        %(low)s,
        %(value)s,
        %(volume)s
    )
    ON CONFLICT (index_id, begin_ts)
    WHERE index_id IS NOT NULL
    DO UPDATE SET
        end_ts = EXCLUDED.end_ts,
        open = EXCLUDED.open,
        close = EXCLUDED.close,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        value = EXCLUDED.value,
        volume = EXCLUDED.volume;
"""


UPSERT_SECURITY_CANDLE_1M_SQL = """
    INSERT INTO dwh.candle_1m (
        index_id,
        security_id,
        begin_ts,
        end_ts,
        open,
        close,
        high,
        low,
        value,
        volume
    )
    VALUES (
        %(index_id)s,
        %(security_id)s,
        %(begin_ts)s,
        %(end_ts)s,
        %(open)s,
        %(close)s,
        %(high)s,
        %(low)s,
        %(value)s,
        %(volume)s
    )
    ON CONFLICT (security_id, begin_ts)
    WHERE security_id IS NOT NULL
    DO UPDATE SET
        end_ts = EXCLUDED.end_ts,
        open = EXCLUDED.open,
        close = EXCLUDED.close,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        value = EXCLUDED.value,
        volume = EXCLUDED.volume;
"""


UPSERT_SPLIT_SQL = """
    INSERT INTO dwh.split(
        security_id,
        trade_date,
        ratio_before,
        ratio_after
    )
    VALUES (
        %(security_id)s,
        %(trade_date)s,
        %(ratio_before)s,
        %(ratio_after)s
    )
    ON CONFLICT (security_id, trade_date)
    DO UPDATE SET
        ratio_before = EXCLUDED.ratio_before,
        ratio_after = EXCLUDED.ratio_after
"""


UPSERT_INDEX_COMPOSITION_SQL = """
    INSERT INTO dwh.index_composition (
        index_id,
        security_id,
        date_from,
        date_till
    )
    VALUES (
        %(index_id)s,
        %(security_id)s,
        %(date_from)s,
        %(date_till)s
    )
    ON CONFLICT (index_id, security_id, date_from)
    DO UPDATE SET
        date_till = EXCLUDED.date_till
"""


UPSERT_CURRENCY_SQL = """
    INSERT INTO dwh.currency (
        cbr_id,
        name,
        eng_name,
        nominal,
        iso_num_code,
        iso_char_code
    )
    VALUES (
        %(cbr_id)s,
        %(name)s,
        %(eng_name)s,
        %(nominal)s,
        %(iso_num_code)s,
        %(iso_char_code)s
    )
    ON CONFLICT (cbr_id)
    DO UPDATE SET
        name = EXCLUDED.name,
        eng_name = EXCLUDED.eng_name,
        nominal = EXCLUDED.nominal,
        iso_num_code = EXCLUDED.iso_num_code,
        iso_char_code = EXCLUDED.iso_char_code
"""


UPSERT_CURRENCY_RATE_SQL = """
    INSERT INTO dwh.currency_rate (
        currency_id,
        rate_date,
        nominal,
        rate_value,
        unit_rate
    )
    VALUES (
        %(currency_id)s,
        %(rate_date)s,
        %(nominal)s,
        %(rate_value)s,
        %(unit_rate)s
    )
    ON CONFLICT (currency_id, rate_date)
    DO UPDATE SET
        nominal = EXCLUDED.nominal,
        rate_value = EXCLUDED.rate_value,
        unit_rate = EXCLUDED.unit_rate
"""


UPSERT_KEY_RATE_SQL = """
    INSERT INTO dwh.key_rate(
        rate_date,
        rate
    )
    VALUES (
        %(rate_date)s,
        %(rate)s
    )
    ON CONFLICT (rate_date)
    DO UPDATE SET
        rate = EXCLUDED.rate
"""


UPSERT_CALENDAR_SQL = """
    INSERT INTO dwh.calendar(
        calendar_date,
        period,
        year,
        quarter,
        month_name,
        month_num,
        day_of_month,
        day_of_week,
        day_of_week_name
    )
    VALUES (
        %(calendar_date)s,
        %(period)s,
        %(year)s,
        %(quarter)s,
        %(month_name)s,
        %(month_num)s,
        %(day_of_month)s,
        %(day_of_week)s,
        %(day_of_week_name)s
    )
    ON CONFLICT (calendar_date)
    DO UPDATE SET
        period = EXCLUDED.period,
        year = EXCLUDED.year,
        quarter = EXCLUDED.quarter,
        month_name = EXCLUDED.month_name,
        month_num = EXCLUDED.month_num,
        day_of_month = EXCLUDED.day_of_month,
        day_of_week = EXCLUDED.day_of_week,
        day_of_week_name = EXCLUDED.day_of_week_name;
"""


UPSERT_DIVIDEND_SQL = """
    INSERT INTO dwh.dividend(
        security_id,
        registry_close_date,
        dividend_value,
        currency_code
    )
    VALUES (
        %(security_id)s,
        %(registry_close_date)s,
        %(dividend_value)s,
        %(currency_code)s
    )
    ON CONFLICT (security_id, registry_close_date)
    DO UPDATE SET
        dividend_value = EXCLUDED.dividend_value,
        currency_code = EXCLUDED.currency_code;
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


def upsert_index_daily(rows: list[dict[str, object]]) -> None:
    """Добавляет и актуализирует дневную историю торгов индексов."""
    if not rows:
        return

    logger.debug("Начата запись в dwh.index_daily")

    with (
        get_connection() as connection,
        connection.cursor() as cursor,
    ):
        cursor.executemany(
            UPSERT_INDEX_DAILY_SQL,
            rows,
        )

    logger.debug(
        "Записано %d строк в dwh.index_daily",
        len(rows),
    )


def upsert_candle_1m(rows: list[dict[str, object]], instrument_type: str) -> None:
    """Добавляет и актуализирует данные по минутным свечам."""

    if not rows:
        return

    if instrument_type == "index":
        sql = UPSERT_INDEX_CANDLE_1M_SQL
    elif instrument_type == "security":
        sql = UPSERT_SECURITY_CANDLE_1M_SQL
    else:
        raise ValueError(f"Unknown instrument type: {instrument_type}")

    logger.debug("Начата запись в dwh.candle_1m")

    with (
        get_connection() as connection,
        connection.cursor() as cursor,
    ):
        cursor.executemany(sql, rows)

    logger.debug(
        "%s. Записано %d строк в dwh.candle_1m",
        instrument_type,
        len(rows),
    )


def upsert_split(rows: list[dict[str, object]]) -> None:
    """Добавляет и актуализирует данные по дроблению и сплтиу акций."""

    if not rows:
        return

    logger.debug("Начата запись в dwh.split")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_SPLIT_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.split", len(rows))


def upsert_index_composition(rows: list[dict[str, object]]) -> None:
    """Добавляет и актуализирует данные по составу индексов."""
    if not rows:
        return

    logger.debug("Начата запись в dwh.index_composition")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_INDEX_COMPOSITION_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.index_composition", len(rows))


def upsert_currency(rows: list[dict[str, object]]) -> None:
    """Актуализация справочника валют ЦБ dwh.currency"""
    if not rows:
        return

    logger.debug("Начата запись в dwh.currency")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_CURRENCY_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.currency", len(rows))


def upsert_currency_rate(rows: list[dict[str, object]]) -> None:
    """Актуализация справочника валют ЦБ dwh.currency_rate"""
    if not rows:
        return

    logger.debug("Начата запись в dwh.currency_rate")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_CURRENCY_RATE_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.currency_rate", len(rows))


def upsert_key_rate(rows: list[dict[str, object]]) -> None:
    "Добавляет и актуализирует историю ключевой ставки ЦБ."
    if not rows:
        return

    logger.debug("Начата запись в dwh.key_rate")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_KEY_RATE_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.key_rate", len(rows))


def upsert_calendar(rows: list[dict[str, object]]) -> None:
    "Добавляет и актуализирует данные dwh.calendar."
    if not rows:
        return

    logger.debug("Начата запись в dwh.calendar")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_CALENDAR_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.calendar", len(rows))


def upsert_dividend(rows: list[dict[str, object]]) -> None:
    "Добавляет и актуализирует данные dwh.dividend."
    if not rows:
        return

    logger.debug("Начата запись в dwh.dividend")
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_DIVIDEND_SQL,
            rows,
        )
    logger.debug("Записано %d строк в dwh.dividend", len(rows))
