
-- DataLens: security_splits
-- История сплитов и консолидаций акций.
-- Тип события и коэффициент изменения количества акций
-- определяются по ratio_before и ratio_after.

SELECT
    s.secid,
    sp.trade_date,
    sp.ratio_before,
    sp.ratio_after,
    CASE
        WHEN sp.ratio_after > sp.ratio_before THEN 'Сплит'
        WHEN sp.ratio_after < sp.ratio_before THEN 'Консолидация'
        ELSE 'Без изменения'
    END AS event_type,
    sp.ratio_after::numeric
        / NULLIF(sp.ratio_before, 0) AS split_ratio

FROM dwh.split AS sp

JOIN dwh.security AS s
    ON s.security_id = sp.security_id
