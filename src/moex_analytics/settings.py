import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


# Scope проекта
with (PROJECT_ROOT / "config" / "scope.toml").open("rb") as file:
    scope = tomllib.load(file)

SELECTED_SECURITIES = scope["moex"]["securities"]["selected"]
SECURITY_BOARD = scope["moex"]["securities"]["board"]

SELECTED_INDICES = scope["moex"]["indices"]
CBR_CURRENCIES = scope["cbr"]["currencies"]

HISTORY_DATE_FROM = scope["history"]["date_from"]
HISTORY_DATE_TO = scope["history"]["date_to"]


# PostgreSQL
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = int(os.environ["POSTGRES_PORT"])
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]


# T-Invest
T_INVEST_TOKEN = os.getenv("T_INVEST_TOKEN")
T_INVEST_CERT_PATH = PROJECT_ROOT / "certs" / "russian-trusted-ca.pem"
