
CREATE SCHEMA IF NOT EXISTS dwh;

-- Справочник ценных бумаг MOEX
CREATE TABLE dwh.security (
    security_id BIGINT GENERATED ALWAYS AS IDENTITY,
    secid TEXT NOT NULL,
    short_name TEXT,
    face_value DOUBLE PRECISION,
    name TEXT,
    face_currency_code TEXT,
    issue_size BIGINT,
    isin TEXT,
    latin_name TEXT,
    reg_number TEXT,
    currency_code TEXT,
    security_type_code TEXT,
    list_level SMALLINT,
    prev_date DATE,
    tbank_uid UUID,

    CONSTRAINT pk_security PRIMARY KEY (security_id),
    CONSTRAINT uq_security_secid UNIQUE (secid),
    CONSTRAINT uq_security_tbank_uid UNIQUE (tbank_uid)
);


-- Справочник индексов MOEX
CREATE TABLE dwh.index (
    index_id BIGINT GENERATED ALWAYS AS IDENTITY,
    index_code TEXT NOT NULL,
    short_name TEXT,
    analytics_from DATE,
    analytics_till DATE,

    CONSTRAINT pk_index PRIMARY KEY (index_id),
    CONSTRAINT uq_index_code UNIQUE (index_code)
);


-- Справочник дат
CREATE TABLE dwh.calendar (
    calendar_date DATE NOT NULL,
    "period" INTEGER NOT NULL,
    "year" SMALLINT NOT NULL,
    "quarter" SMALLINT NOT NULL,
    month_num SMALLINT NOT NULL,
    month_name TEXT NOT NULL,
    day_of_month SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    day_of_week_name TEXT NOT NULL,

    CONSTRAINT pk_calendar PRIMARY KEY (calendar_date)
);


-- Справочник валют ЦБ
CREATE TABLE dwh.currency (
    currency_id BIGINT GENERATED ALWAYS AS IDENTITY,
    cbr_id TEXT NOT NULL,
    name TEXT NOT NULL,
    eng_name TEXT,
    nominal INTEGER NOT NULL,
    iso_num_code SMALLINT,
    iso_char_code TEXT NOT NULL,

    CONSTRAINT pk_currency PRIMARY KEY (currency_id),
    CONSTRAINT uq_cbr UNIQUE (cbr_id)
);


-- Ключевая ставка ЦБ
CREATE TABLE dwh.key_rate (
    rate_date DATE,
    rate NUMERIC NOT NULL,

    CONSTRAINT pk_key_rate PRIMARY KEY (rate_date)
);


-- Дневные данные по акциям
CREATE TABLE dwh.security_daily (
    security_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    num_trades BIGINT,
    value DOUBLE PRECISION,
    open DOUBLE PRECISION,
    low DOUBLE PRECISION,
    high DOUBLE PRECISION,
    waprice DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,

    CONSTRAINT pk_security_daily PRIMARY KEY (security_id, trade_date),
    CONSTRAINT fk_security_daily FOREIGN KEY (security_id) REFERENCES dwh.security(security_id)
);

-- Дневные данные по индексам
CREATE TABLE dwh.index_daily(
    index_id BIGINT NOT NULL,
    board_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    close DOUBLE PRECISION,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    capitalization DOUBLE PRECISION,
    divisor DOUBLE PRECISION,

    CONSTRAINT pk_index_daily PRIMARY KEY (index_id, trade_date),
    CONSTRAINT fk_index_daily FOREIGN KEY (index_id) REFERENCES dwh.index(index_id)
);


-- Минутные свечи акций и индексов
CREATE TABLE dwh.candle_1m (
    security_id BIGINT,
    index_id BIGINT,
    begin_ts TIMESTAMP NOT NULL,
    end_ts TIMESTAMP NOT NULL,
    open DOUBLE PRECISION,
    close DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    value DOUBLE PRECISION,
    volume DOUBLE PRECISION,

    CONSTRAINT fk_candle_1m_security FOREIGN KEY (security_id) REFERENCES dwh.security(security_id),
    CONSTRAINT fk_candle_1m_index FOREIGN KEY (index_id) REFERENCES dwh.index(index_id),
    CONSTRAINT chk_candle_1m_instrument
        CHECK (
            (security_id IS NOT NULL AND index_id IS NULL)
            OR
            (security_id IS NULL AND index_id IS NOT NULL)
        )
);


-- Дивидентные события
CREATE TABLE dwh.dividend(
    security_id BIGINT NOT NULL,
    registry_close_date DATE NOT NULL,
    dividend_value NUMERIC,
    currency_code TEXT,

    CONSTRAINT pk_dividend PRIMARY KEY (security_id, registry_close_date),
    CONSTRAINT fk_dividend FOREIGN KEY (security_id) REFERENCES dwh.security(security_id)
);


-- Сплит и консолидация акций
CREATE TABLE dwh.split(
    security_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    ratio_before NUMERIC NOT NULL,
    ratio_after NUMERIC NOT NULL,

    CONSTRAINT pk_split PRIMARY KEY (security_id, trade_date),
    CONSTRAINT fk_split FOREIGN KEY (security_id) REFERENCES dwh.security(security_id)
);

-- Вхождение акций в индекс
CREATE TABLE dwh.index_composition(
    index_id BIGINT NOT NULL,
    security_id BIGINT NOT NULL,
    date_from DATE NOT NULL,
    date_till DATE NOT NUll,

    CONSTRAINT pk_index_composition PRIMARY KEY (index_id, security_id, date_from),
    CONSTRAINT fk_index_composition_index FOREIGN KEY (index_id) REFERENCES dwh.index(index_id),
    CONSTRAINT fk_index_composition_security FOREIGN KEY (security_id) REFERENCES dwh.security(security_id)
);


-- Курсы валют ЦБ
CREATE TABLE dwh.currency_rate(
    currency_id BIGINT NOT NULL,
    rate_date DATE NOT NULL,
    nominal INTEGER NOT NULL,
    rate_value NUMERIC NOT NULL,
    unit_rate NUMERIC NOT NULL,

    CONSTRAINT pk_currency_rate PRIMARY KEY (currency_id, rate_date),
    CONSTRAINT fk_currency_rate FOREIGN KEY  (currency_id) REFERENCES dwh.currency(currency_id)
);
