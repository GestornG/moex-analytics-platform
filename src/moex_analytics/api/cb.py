"""
Получение данных Центрального Банка РФ через www.cbr.ru XML

Модуль отвечает за HTTP-запросы к cbr, проверку ответов
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
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


def get_xml(url: str, timeout: int = 30, params: dict[str, Any] | None = None) -> bytes:
    """Реализация запроса requests.get с исключением."""
    try:
        logger.debug(
            "HTTP GET: url=%s, params=%s",
            url,
            params,
        )
        response = session.get(url=url, timeout=timeout, params=params)

        response.raise_for_status()
        return response.content

    except requests.RequestException:
        logger.exception(
            "HTTP GET failed: url=%s, params=%s",
            url,
            params,
        )
        raise


def get_currency_cb() -> bytes:
    """Выгружает данные по справочнику валют ЦБ."""
    url = "http://www.cbr.ru/scripts/XML_valFull.asp"
    return get_xml(url)


def get_currency_rate(params: dict[str, str]) -> bytes:
    """Выгружает динамику котировок по валюте за период."""
    url = "https://www.cbr.ru/scripts/XML_dynamic.asp"
    return get_xml(url=url, params=params)
