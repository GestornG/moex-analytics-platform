"""
Получение данных Московской биржи через MOEX ISS API.

Модуль отвечает за HTTP-запросы к MOEX, проверку ответов
и возврат исходных данных для дальнейшей обработки в ETL.
"""

from typing import Any

import requests


def get_list_shares(
    engine: str = "stock", market: str = "shares", board: str = "TQBR"
) -> dict[str, Any]:
    url = (
        f"https://iss.moex.com/iss/engines/{engine}/markets/"
        f"{market}/boards/{board}/securities.json"
    )
    response = requests.get(url=url, timeout=30)
    response.raise_for_status()
    return response.json()
