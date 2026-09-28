"""Общие вспомогательные функции ETL-слоя."""

import pandas as pd


def dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    """Преобразует DataFrame в строки для параметризованного SQL-запроса.

    Значения pandas/NumPy, представляющие пропуски, заменяются на ``None``,
    чтобы psycopg передавал их в PostgreSQL как ``NULL``.
    """
    df = df.astype(object).where(pd.notna(df), None)
    columns = [str(column) for column in df.columns]

    rows: list[dict[str, object]] = []
    for values in df.itertuples(index=False, name=None):
        rows.append(dict(zip(columns, values)))

    return rows
