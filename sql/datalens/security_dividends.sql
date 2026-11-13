-- DataLens: security_dividends
-- Дивидендные события акций и рублёвый эквивалент выплат.
-- Для валютных дивидендов используется последний доступный
-- курс ЦБ на дату закрытия реестра или ранее.

SELECT
    s.secid,
    d.registry_close_date,
    d.dividend_value,
    d.currency_code,
    CASE
        WHEN d.currency_code = 'RUB'
            THEN d.dividend_value
        ELSE d.dividend_value * cr.unit_rate
    END AS dividend_rub

FROM dwh.security AS s

JOIN dwh.dividend AS d
    ON d.security_id = s.security_id

LEFT JOIN dwh.currency AS cur
    ON d.currency_code = cur.iso_char_code

LEFT JOIN LATERAL (
    SELECT cr.unit_rate
    FROM dwh.currency_rate AS cr
    WHERE cr.currency_id = cur.currency_id
      AND cr.rate_date <= d.registry_close_date
    ORDER BY cr.rate_date DESC
    LIMIT 1
) AS cr ON TRUE

ORDER BY s.secid, d.registry_close_date DESC
