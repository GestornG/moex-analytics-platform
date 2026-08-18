import os

import psycopg
from dotenv import load_dotenv

from moex_analytics.settings import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


def get_connection() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
