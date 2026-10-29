
CREATE OR REPLACE VIEW analytics.v_split_factors AS

WITH RECURSIVE events AS (
    SELECT
        security_id,
        trade_date,

        LAG(trade_date) OVER (
            PARTITION BY security_id
            ORDER BY trade_date
        ) AS date_from,

        ROW_NUMBER() OVER (
            PARTITION BY security_id
            ORDER BY trade_date DESC
        ) AS rn,

        ratio_before::numeric
            / NULLIF(ratio_after, 0) AS factor

    FROM dwh.split
),

factors AS (
    SELECT
        security_id,
        date_from,
        trade_date AS date_to,
        rn,
        factor AS cumulative_factor

    FROM events
    WHERE rn = 1

    UNION ALL

    SELECT
        e.security_id,
        e.date_from,
        e.trade_date,
        e.rn,
        f.cumulative_factor * e.factor

    FROM events e
    JOIN factors f
        ON e.security_id = f.security_id
       AND e.rn = f.rn + 1
)

SELECT
    security_id,
    date_from,
    date_to,
    cumulative_factor AS split_factor

FROM factors
WHERE cumulative_factor <> 1;


COMMENT ON VIEW analytics.v_split_factors IS
    'Интервальные накопленные коэффициенты корректировки цен на сплиты и консолидации.';

COMMENT ON COLUMN analytics.v_split_factors.security_id IS
    'Идентификатор акции.';

COMMENT ON COLUMN analytics.v_split_factors.date_from IS
    'Начало периода включительно; NULL означает отсутствие нижней границы.';

COMMENT ON COLUMN analytics.v_split_factors.date_to IS
    'Конец периода исключительно; дата корпоративного события.';

COMMENT ON COLUMN analytics.v_split_factors.split_factor IS
    'Накопленный коэффициент корректировки исторических цен.';
