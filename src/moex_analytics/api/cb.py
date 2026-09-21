"""
Получение данных Центрального Банка РФ через www.cbr.ru XML

Модуль отвечает за HTTP-запросы к cbr, проверку ответов
и возврат исходных данных для дальнейшей обработки в ETL.
"""

import logging
from datetime import date
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)

session = requests.Session()
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


def get_xml(
    url: str,
    timeout: int = 30,
    params: dict[str, Any] | None = None,
) -> bytes:
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


def get_key_rate(date_from: date, date_to: date) -> bytes:
    """Выгружает динамику значений ключевой ставки Банка России за период."""
    url_key_rate = "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"

    headers_key_rate = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://web.cbr.ru/KeyRateXML",
    }

    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <KeyRateXML xmlns="http://web.cbr.ru/">
                <fromDate>{date_from.strftime("%Y-%m-%dT00:00:00")}</fromDate>
                <ToDate>{date_to.strftime("%Y-%m-%dT00:00:00")}</ToDate>
            </KeyRateXML>
        </soap:Body>
    </soap:Envelope>
    """

    try:
        logger.debug(
            "HTTP POST: url=%s",
            url_key_rate,
        )
        response = session.post(
            url=url_key_rate, timeout=30, headers=headers_key_rate, data=soap_body
        )

        response.raise_for_status()
        return response.content

    except requests.RequestException:
        logger.exception(
            "HTTP POST failed: url=%s, headers=%s, data=%s",
            url_key_rate,
            headers_key_rate,
            soap_body,
        )
        raise
