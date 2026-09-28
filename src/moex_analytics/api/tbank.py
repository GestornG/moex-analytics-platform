"""
Получение данных Т-банка через sandbox-invest-public-api.tbank.ru:443

Модуль отвечает за HTTP-запросы к api.tbank.ru, проверку ответов
и возврат исходных данных для дальнейшей обработки в ETL.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from moex_analytics.settings import T_INVEST_CERT_PATH, T_INVEST_TOKEN

BASE_SANDBOX_URL = "https://sandbox-invest-public-api.tbank.ru:443/rest"

logger = logging.getLogger(__name__)

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],
)

session = requests.Session()

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry),
)
session.headers.update(
    {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {T_INVEST_TOKEN}",
    }
)


def post_json(
    endpoint: str, payload: dict[str, Any], timeout: int = 30
) -> dict[str, Any]:
    """Выполняет POST-запрос к T-Invest REST API."""
    url = f"{BASE_SANDBOX_URL}/{endpoint}"
    try:
        logger.debug("HTTP POST: url=%s, json=%s", url, payload)
        response = session.post(
            url=url,
            json=payload,
            verify=str(T_INVEST_CERT_PATH),
            timeout=timeout,
        )

        try:
            data = response.json()
        except ValueError:
            data = None

        if isinstance(data, dict) and str(data.get("code")) == "40003":
            raise RuntimeError(
                "T-Invest token недействителен или неактивен. "
                "Обновите T_INVEST_TOKEN в .env."
            )

        response.raise_for_status()

        if data is None:
            raise ValueError("T-Invest API вернул ответ не в формате JSON.")
        return data

    except requests.RequestException:
        logger.exception("HTTP POST failed: url=%s", url)
        raise


def find_instrument(isin: str) -> dict[str, Any]:
    """Ищет информацию по указанному инструменту.
    Параметры:
        isin - Международный идентификатор бумаги ISIN."""

    endpoint = "tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument"
    payload = {
        "query": isin,
        "instrumentKind": "INSTRUMENT_TYPE_SHARE",
    }

    return post_json(endpoint=endpoint, payload=payload)


def get_dividends(instrument_uid: str, date_from: str, date_to: str) -> dict[str, Any]:
    """Выгружает дивиденды по указанной бумаге за период.
    Параамтеры:
        instrument_uid - технический уникальный ID инструмента у T-Bank.
        date_from | date_to - период за который выгружаются дивиденды.
    """
    endpoint = "tinkoff.public.invest.api.contract.v1.InstrumentsService/GetDividends"
    payload = {
        "from": date_from,
        "to": date_to,
        "instrumentId": str(instrument_uid),
    }
    return post_json(endpoint=endpoint, payload=payload)


def check_t_invest_token() -> bool:
    """Проверяет наличие а актуальность токена для песочницы T-Invest.
    Возвращает:
        True - когда токен рабочий, иначе False."""
    endpoint = "tinkoff.public.invest.api.contract.v1.UsersService/GetInfo"

    try:
        post_json(endpoint=endpoint, payload={})
        return True
    except RuntimeError:
        logger.warning(
            "T-Invest token недействителен. Загрузка T-Invest данных будет пропущена."
        )
        return False
