-- candle_1m — уникальность и быстрый поиск свечей акций
CREATE UNIQUE INDEX uq_candle_1m_security_begin
ON dwh.candle_1m (security_id, begin_ts)
WHERE security_id IS NOT NULL;


-- candle_1m — уникальность и быстрый поиск свечей индексов
CREATE UNIQUE INDEX uq_candle_1m_index_begin
ON dwh.candle_1m (index_id, begin_ts)
WHERE index_id IS NOT NULL;


-- security_daily — выборка всех акций на конкретную дату
CREATE INDEX ix_security_daily_trade_date
ON dwh.security_daily (trade_date);


-- index_daily — выборка всех индексов на конкретную дату
CREATE INDEX ix_index_daily_trade_date
ON dwh.index_daily (trade_date);


-- currency_rate — выборка курсов всех валют на конкретную дату
CREATE INDEX ix_currency_rate_rate_date
ON dwh.currency_rate (rate_date);


-- dividend — поиск дивидендных событий по дате
CREATE INDEX ix_dividend_registry_close_date
ON dwh.dividend (registry_close_date);


-- split — поиск сплитов и консолидаций по дате
CREATE INDEX ix_split_trade_date
ON dwh.split (trade_date);


-- index_composition — поиск индексов, в которых участвовала акция
CREATE INDEX ix_index_composition_security_id
ON dwh.index_composition (security_id);
