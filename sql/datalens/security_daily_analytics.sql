-- DataLens: security_daily_analytics
-- Дневные котировки и торговая активность акций.
-- Исторические OHLC-цены корректируются на сплиты
-- и консолидации через analytics.v_split_factors.

SELECT
    s.security_id,
    s.secid,
    sd.trade_date,

    sd.open,
    sd.high,
    sd.low,
    sd.close,
    sd.volume,
    sd.value,

    COALESCE(sf.split_factor, 1) as split_factor,

    (sd.open * COALESCE(sf.split_factor, 1))::numeric as open_adj,
    (sd.high * COALESCE(sf.split_factor, 1))::numeric as high_adj,
    (sd.low * COALESCE(sf.split_factor, 1))::numeric as low_adj,
    (sd.close * COALESCE(sf.split_factor, 1))::numeric as close_adj

FROM dwh.security as s

JOIN dwh.security_daily as sd
    on s.security_id = sd.security_id

LEFT JOIN analytics.v_split_factors as sf
    on s.security_id = sf.security_id
    AND (
        sf.date_from IS NULL
        OR sf.date_from <= sd.trade_date
    )
    AND sf.date_to > sd.trade_date
