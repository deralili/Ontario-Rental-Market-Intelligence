-- =========================================================
-- Ontario Rental Market Intelligence
-- Clean Layer
-- =========================================================


-- =========================================================
-- 1. Clean CMHC Rental Market Data
-- =========================================================

DROP TABLE IF EXISTS clean.cmhc_rental_market;

CREATE TABLE clean.cmhc_rental_market AS

SELECT
    edition_year,
    observation_year,

    -- Standardize CMHC market names
    CASE market_raw
        WHEN 'Barrie CMA'
            THEN 'Barrie'
        WHEN 'Belleville CMA'
            THEN 'Belleville–Quinte West'
        WHEN 'Belleville - Quinte West CMA'
            THEN 'Belleville–Quinte West'
        WHEN 'Brantford CMA'
            THEN 'Brantford'
        WHEN 'Greater Sudbury/Grand Sudbury CMA'
            THEN 'Greater Sudbury'
        WHEN 'Guelph CMA'
            THEN 'Guelph'
        WHEN 'Hamilton CMA'
            THEN 'Hamilton'
        WHEN 'Kingston CMA'
            THEN 'Kingston'
        WHEN 'Kitchener-Cambridge-Waterloo CMA'
            THEN 'Kitchener–Cambridge–Waterloo'
        WHEN 'London CMA'
            THEN 'London'
        WHEN 'Oshawa CMA'
            THEN 'Oshawa'
        WHEN 'Ottawa-Gatineau CMA (Ont. part)'
            THEN 'Ottawa–Gatineau (Ontario part)'
        WHEN 'St. Catharines-Niagara CMA'
            THEN 'St. Catharines–Niagara'
        WHEN 'Thunder Bay CMA'
            THEN 'Thunder Bay'
        WHEN 'Toronto CMA'
            THEN 'Toronto'
        WHEN 'Windsor CMA'
            THEN 'Windsor'
        ELSE NULL
    END AS market,

    -- Standardize Bachelor terminology to Studio
    CASE
        WHEN unit_type_raw = 'Bachelor'
            THEN 'Studio'
        ELSE unit_type_raw
    END AS unit_type,

    measure,

    -- Convert valid source values to numeric.
    -- Source suppression symbols such as ** and ++
    -- remain preserved separately in value_raw.
    CASE
        WHEN REPLACE(value_raw, ',', '') ~ '^-?[0-9]+(\.[0-9]+)?$'
            THEN REPLACE(value_raw, ',', '')::NUMERIC
        ELSE NULL
    END AS value,

    -- Preserve original source value for QA and traceability
    value_raw,

    -- Preserve CMHC reliability information
    reliability_code,

    -- Preserve published change indicator where applicable
    change_indicator,

    -- Preserve source worksheet
    source_sheet

FROM raw.cmhc_rental_market;


-- =========================================================
-- 2. Clean Statistics Canada Family Income Data
-- =========================================================

DROP TABLE IF EXISTS clean.statcan_family_income;

CREATE TABLE clean.statcan_family_income AS

SELECT
    ref_date AS observation_year,

    -- Standardize StatsCan geography names to the same
    -- market names used in the CMHC clean table.
    CASE geo
        WHEN 'Barrie, Ontario'
            THEN 'Barrie'
        WHEN 'Belleville-Quinte West, Ontario'
            THEN 'Belleville–Quinte West'
        WHEN 'Brantford, Ontario'
            THEN 'Brantford'
        WHEN 'Greater Sudbury, Ontario'
            THEN 'Greater Sudbury'
        WHEN 'Guelph, Ontario'
            THEN 'Guelph'
        WHEN 'Hamilton, Ontario'
            THEN 'Hamilton'
        WHEN 'Kingston, Ontario'
            THEN 'Kingston'
        WHEN 'Kitchener-Cambridge-Waterloo, Ontario'
            THEN 'Kitchener–Cambridge–Waterloo'
        WHEN 'London, Ontario'
            THEN 'London'
        WHEN 'Oshawa, Ontario'
            THEN 'Oshawa'
        WHEN 'Ottawa-Gatineau, Ontario part'
            THEN 'Ottawa–Gatineau (Ontario part)'
        WHEN 'St. Catharines-Niagara, Ontario'
            THEN 'St. Catharines–Niagara'
        WHEN 'Thunder Bay, Ontario'
            THEN 'Thunder Bay'
        WHEN 'Toronto, Ontario'
            THEN 'Toronto'
        WHEN 'Windsor, Ontario'
            THEN 'Windsor'
        ELSE NULL
    END AS market,

    -- Analysis measure
    value AS median_after_tax_family_income,

    -- Preserve source fields for traceability
    geo AS geo_raw,
    dguid,
    census_family_type,
    family_type_composition,
    statistics,
    uom,
    scalar_factor,
    status,
    symbol,
    terminated,
    decimals

FROM raw.statcan_family_income;


-- =========================================================
-- 3. Reshape CMHC Measures to Analysis-Ready Wide Format
-- =========================================================

DROP TABLE IF EXISTS clean.cmhc_market_year_unit;

CREATE TABLE clean.cmhc_market_year_unit AS

SELECT
    observation_year,
    market,
    unit_type,

    MAX(value) FILTER (
        WHERE measure = 'Average Rent'
    ) AS average_rent,

    MAX(value) FILTER (
        WHERE measure = 'Vacancy Rate'
    ) AS vacancy_rate,

    MAX(value) FILTER (
        WHERE measure = 'Rental Universe'
    ) AS rental_universe,

    MAX(value) FILTER (
        WHERE measure = 'Percentage Change in Average Rent'
    ) AS published_rent_change_pct,

    MAX(value) FILTER (
        WHERE measure = 'Turnover Rate'
    ) AS turnover_rate

FROM clean.cmhc_rental_market

GROUP BY
    observation_year,
    market,
    unit_type;
	