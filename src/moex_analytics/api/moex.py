"""
Получение данных Московской биржи через MOEX ISS API.

Модуль отвечает за HTTP-запросы к MOEX, проверку ответов
и возврат исходных данных для дальнейшей обработки в ETL.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


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
        response = requests.get(url=url, timeout=timeout, params=params)
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        logger.exception(
            "HTTP GET failed: url=%s, params=%s",
            url,
            params,
        )
        raise


def get_list_shares(
    engine: str = "stock", market: str = "shares", board: str = "TQBR"
) -> dict[str, Any]:
    """Выгрузить справочник акций по указанным параметрам."""
    url = (
        f"https://iss.moex.com/iss/engines/{engine}/markets/"
        f"{market}/boards/{board}/securities.json"
    )
    return get_json(url)
