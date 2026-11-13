-- Select all rows from 'DW'
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

    ROUND((sd.open * COALESCE(sf.split_factor, 1))::numeric, 2) as open_adj,
    ROUND((sd.high * COALESCE(sf.split_factor, 1))::numeric, 2) as high_adj,
    ROUND((sd.low * COALESCE(sf.split_factor, 1))::numeric, 2) as low_adj,
    ROUND((sd.close * COALESCE(sf.split_factor, 1))::numeric, 2) as close_adj

FROM dwh.security as s

LEFT JOIN dwh.security_daily as sd
    on s.security_id = sd.security_id

LEFT JOIN analytics.v_split_factors as sf
    on s.security_id = sf.security_id
    AND (
        sf.date_from IS NULL
        OR sf.date_from <= sd.trade_date
    )
    AND sf.date_to > sd.trade_date

limit 1500;
