"""
Получение данных Московской биржи через MOEX ISS API.

Модуль отвечает за HTTP-запросы к MOEX, проверку ответов
и возврат исходных данных для дальнейшей обработки в ETL.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)

session = requests.Session()

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry),
)


def get_json(
    url: str, timeout: int = 30, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Реализация запроса requests.get с исключением."""
    try:
        logger.debug(
            "HTTP GET: url=%s, params=%s",
            url,
            params,
        )
        # response = requests.get(url=url, timeout=timeout, params=params)
        response = session.get(url=url, timeout=timeout, params=params)

        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        logger.exception(
            "HTTP GET failed: url=%s, params=%s",
            url,
            params,
        )
        raise


def get_stock_security(
    engine: str = "stock", market: str = "shares", board: str = "TQBR"
) -> dict[str, Any]:
    """Выгрузить справочник акций по указанным параметрам."""
    url = (
        f"https://iss.moex.com/iss/engines/{engine}/markets/"
        f"{market}/boards/{board}/securities.json"
    )
    return get_json(url)


def get_stock_index() -> dict[str, Any]:
    """Выгрузить справочник индексов фондового рынка."""
    url = (
        "https://iss.moex.com/iss/statistics/engines/stock/markets/index/analytics.json"
    )
    return get_json(url)


def get_available_date_range(
    security: str,
    engine: str = "stock",
    market: str = "shares",
) -> dict[str, Any]:
    """Получить интервал дат, доступных в истории для рынка по заданному режиму торгов."""
    url = (
        f"https://iss.moex.com/iss/history/engines/{engine}"
        f"/markets/{market}/securities/{security}/dates.json"
    )
    return get_json(url)


def get_security_daily_history(
    security: str,
    params: dict[str, Any],
    engine: str = "stock",
    market: str = "shares",
    board: str = "TQBR",
) -> dict[str, Any]:
    """Для заданных диапазонов дат выгружает дневную историю торгов по акции в указанном режиме торгов.
    params: содержит словарь параметров с указанием периода.
    """
    url = (
        f"https://iss.moex.com/iss/history/engines/{engine}"
        f"/markets/{market}/boards/{board}/securities/{security}.json"
    )
    return get_json(url, params=params)


def get_index_daily_history(
    index: str,
    board: str,
    params: dict[str, Any],
    engine: str = "stock",
    market: str = "index",
) -> dict[str, Any]:
    """По заданному диапазону выгружает дневную историю торгов по индексам в указанном режиме торгов.
    params: содержит словарь параметров с указанием периодов.
    """
    url = (
        f"https://iss.moex.com/iss/history/engines/{engine}"
        f"/markets/{market}/boards/{board}/securities/{index}.json"
    )
    return get_json(url=url, params=params)


def get_available_candle_range(
    security: str,
    board: str,
    market: str,
    engine: str = "stock",
) -> dict[str, Any]:
    """По указанным параметрам выгружает период доступных свечей."""
    url = (
        f"https://iss.moex.com/iss/engines/{engine}/markets/{market}"
        f"/boards/{board}/securities/{security}/candleborders.json"
    )
    return get_json(url=url)


def get_candle_1м(
    market: str,
    board: str,
    security: str,
    params: dict[str, Any],
    engine: str = "stock",
) -> dict[str, Any]:
    """Для заданного периода выгружает минутные свечи по указанному инструменту.
    params:
        "interval": указывает группу выгружаемых данных. 1 - минутные свечи,
        "from": дата начала периода,
        "till": дата окончания периода,
        "start": указывает строку с которой нужно начать выгрузку (для пагинации)"""

    url = (
        f"https://iss.moex.com/iss/engines/{engine}/markets/{market}"
        f"/boards/{board}/securities/{security}/candles.json"
    )
    return get_json(url=url, params=params)
