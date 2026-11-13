CREATE AGGREGATE product(numeric) (
    SFUNC = numeric_mul,
    STYPE = numeric,
    INITCOND = '1'
);

SELECT
    sd.security_id,
    sd.trade_date,
    public.product(sp.ratio_before::numeric) AS total_before,
    public.product(sp.ratio_after::numeric) AS total_after

FROM dwh.security_daily as sd
LEFT JOIN dwh.split as sp
    ON sd.security_id = sp.security_id
    AND sd.trade_date < sp.trade_date
WHERE sp.ratio_before IS NOT NULL
GROUP BY
    sd.security_id,
    sd.trade_date
LIMIT 25;



SELECT
    s1.security_id,
    s2.trade_date as date_from,
    s1.trade_date as date_to,
    (1 / s1.ratio_after / COALESCE(s2.ratio_after, 1))::DECIMAL
        AS split_event,
    (s1.ratio_before * COALESCE(s2.ratio_before, 1))::DECIMAL
        AS consolidation_event

FROM dwh.split as s1
LEFT JOIN dwh.split as s2
    on s1.security_id = s2.security_id
    AND s1.trade_date > s2.trade_date;





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
        e.trade_date AS date_to,
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
WHERE cumulative_factor <> 1
ORDER BY security_id, date_from NULLS FIRST;



select
  s.secid,
  d.registry_close_date,
  d.dividend_value,
  d.currency_code,
  d.dividend_value * coalesce (cr.rate_value, 1) as dividend_rub

from dwh.security as s
join dwh.dividend as d
  on d.security_id = s.security_id
left join dwh.currency as cur
  on d.currency_code = cur.iso_char_code
left join dwh.currency_rate as cr
    ON cr.currency_id = cur.currency_id
    and d.registry_close_date = cr.rate_date
limit 100


