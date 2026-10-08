-- =========================================================
-- Ontario Rental Market Intelligence
-- Raw Staging Tables
-- =========================================================

CREATE TABLE IF NOT EXISTS raw.cmhc_rental_market (
    edition_year       INTEGER,
    observation_year   INTEGER,
    market_raw         TEXT,
    unit_type_raw      TEXT,
    measure            TEXT,
    value_raw          TEXT,
    reliability_code   TEXT,
    change_indicator   TEXT,
    source_sheet       TEXT
);


-- =========================================================
-- Statistics Canada T1 Family File
-- Table 11-10-0017-01
-- =========================================================

CREATE TABLE IF NOT EXISTS raw.statcan_family_income (
    ref_date                 INTEGER,
    geo                      TEXT,
    dguid                    TEXT,
    census_family_type       TEXT,
    family_type_composition  TEXT,
    statistics               TEXT,
    uom                      TEXT,
    scalar_factor            TEXT,
    value                    NUMERIC,
    status                   TEXT,
    symbol                   TEXT,
    terminated               TEXT,
    decimals                 INTEGER
);