from moex_analytics.db.connection import get_connection


def get_securitys_from_db():
    """Возвращает перечень уникальных наименований акций из таблицы dwh.security."""
    with get_connection() as connection:
        rows = connection.execute("SELECT DISTINCT(secid) FROM dwh.security").fetchall()
    return {secid for (secid,) in rows}
