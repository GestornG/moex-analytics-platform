"""Общие вспомогательные функции ETL-слоя."""

from datetime import date, timedelta

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


def calculate_missing_date_ranges(
    target_from: date,
    target_to: date,
    loaded_from: date | None,
    loaded_to: date | None,
) -> list[tuple[date, date]]:
    """Возвращает отсутствующие крайние диапазоны дат.
    Параметры:
        target_from - начало целевого диапазона,
        target_to - окончаниее целевого диапазона,
        loaded_from - минимальная загруженная в БД дата,
        loaded_to - максимальная загруженная в БД дата.
    Возвращает:
        Список каржетей содержащих диапазон дат начала - конца выгрузки."""

    ranges: list[tuple[date, date]] = []

    if target_from > target_to:
        return ranges

    if loaded_from is None or loaded_to is None:
        return [(target_from, target_to)]

    if loaded_from <= target_from and loaded_to >= target_to:
        return ranges

    if target_to < loaded_from or target_from > loaded_to:
        return [(target_from, target_to)]

    if target_from < loaded_from:
        ranges.append(
            (
                target_from,
                loaded_from - timedelta(days=1),
            )
        )

    if target_to > loaded_to:
        ranges.append(
            (
                loaded_to + timedelta(days=1),
                target_to,
            )
        )

    return ranges
