import tomllib
from pathlib import Path

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parents[2]

with (PROJECT_ROOT / "config" / "scope.toml").open("rb") as file:
    scope = tomllib.load(file)

SELECTED_SECURITIES = scope["moex"]["securities"]["selected"]
SECURITY_BOARD = scope["moex"]["securities"]["board"]

SELECTED_INDICES = scope["moex"]["indices"]
CBR_CURRENCIES = scope["cbr"]["currencies"]

HISTORY_DATE_FROM = scope["history"]["date_from"]
HISTORY_DATE_TO = scope["history"]["date_to"]
