-- =========================================================
-- Ontario Rental Market Intelligence
-- Analytics Layer
-- =========================================================

-- =========================================================
-- 1. Market-Year-Unit KPIs and Annual Changes
-- =========================================================

CREATE OR REPLACE VIEW analytics.vw_rental_market_kpis AS

WITH annual_data AS (

    SELECT
        observation_year,
        market,
        unit_type,
        average_rent,
        vacancy_rate,
        rental_universe,
        published_rent_change_pct,
        turnover_rate

    FROM clean.cmhc_market_year_unit

),

previous_year AS (

    SELECT
        current_year.*,

        prior_year.average_rent AS previous_average_rent,

        prior_year.rental_universe AS previous_rental_universe

    FROM annual_data AS current_year

    LEFT JOIN annual_data AS prior_year
        ON current_year.market = prior_year.market
        AND current_year.unit_type = prior_year.unit_type
        AND current_year.observation_year =
            prior_year.observation_year + 1

)

SELECT
    observation_year,
    market,
    unit_type,

    -- Published CMHC indicators
    average_rent,
    vacancy_rate,
    rental_universe,
    published_rent_change_pct,
    turnover_rate,

    -- Previous-year reference values
    previous_average_rent,
    previous_rental_universe,

    -- Calculated year-over-year average rent change
    ROUND(
        (
            (average_rent - previous_average_rent)
            / NULLIF(previous_average_rent, 0)
        ) * 100,
        2
    ) AS calculated_rent_yoy_pct,

    -- Calculated year-over-year rental supply growth
    ROUND(
        (
            (rental_universe - previous_rental_universe)
            / NULLIF(previous_rental_universe, 0)
        ) * 100,
        2
    ) AS rental_supply_yoy_pct

FROM previous_year;


-- =========================================================
-- 2. Cumulative Rent Growth Since 2019
-- =========================================================

CREATE OR REPLACE VIEW analytics.vw_cumulative_rent_growth AS

SELECT
    current_year.observation_year,
    current_year.market,
    current_year.unit_type,
    current_year.average_rent,

    baseline.average_rent AS baseline_rent_2019,

    ROUND(
        (
            (current_year.average_rent - baseline.average_rent)
            / NULLIF(baseline.average_rent, 0)
        ) * 100,
        2
    ) AS cumulative_rent_growth_pct

FROM clean.cmhc_market_year_unit AS current_year

LEFT JOIN clean.cmhc_market_year_unit AS baseline
    ON current_year.market = baseline.market
    AND current_year.unit_type = baseline.unit_type
    AND baseline.observation_year = 2019;


-- =========================================================
-- 3. Market-Level Rent-to-Income Indicator
-- =========================================================

CREATE OR REPLACE VIEW analytics.vw_rental_affordability AS

SELECT
    rent.observation_year,
    rent.market,

    rent.average_rent,
    income.median_after_tax_family_income,

    ROUND(
        (
            rent.average_rent * 12
            / NULLIF(income.median_after_tax_family_income, 0)
        ) * 100,
        2
    ) AS rent_to_income_pct

FROM clean.cmhc_market_year_unit AS rent

INNER JOIN clean.statcan_family_income AS income
    ON rent.market = income.market
    AND rent.observation_year = income.observation_year

WHERE rent.unit_type = 'Total';


-- =========================================================
-- 4. Market Comparison
-- =========================================================

CREATE OR REPLACE VIEW analytics.vw_market_comparison AS

SELECT
    kpi.observation_year,
    kpi.market,

    kpi.average_rent,
    kpi.vacancy_rate,
    kpi.rental_universe,
    kpi.turnover_rate,

    kpi.published_rent_change_pct,
    kpi.calculated_rent_yoy_pct,
    kpi.rental_supply_yoy_pct,

    growth.cumulative_rent_growth_pct,

    affordability.median_after_tax_family_income,
    affordability.rent_to_income_pct

FROM analytics.vw_rental_market_kpis AS kpi

LEFT JOIN analytics.vw_cumulative_rent_growth AS growth
    ON kpi.observation_year = growth.observation_year
    AND kpi.market = growth.market
    AND kpi.unit_type = growth.unit_type

LEFT JOIN analytics.vw_rental_affordability AS affordability
    ON kpi.observation_year = affordability.observation_year
    AND kpi.market = affordability.market

WHERE kpi.unit_type = 'Total';


-- =========================================================
-- 5. Market and Unit Type Analysis
-- =========================================================

CREATE OR REPLACE VIEW analytics.vw_market_unit_analysis AS

SELECT
    kpi.observation_year,
    kpi.market,
    kpi.unit_type,

    kpi.average_rent,
    kpi.vacancy_rate,
    kpi.rental_universe,
    kpi.turnover_rate,

    kpi.published_rent_change_pct,
    kpi.calculated_rent_yoy_pct,
    kpi.rental_supply_yoy_pct,

    growth.cumulative_rent_growth_pct

FROM analytics.vw_rental_market_kpis AS kpi

LEFT JOIN analytics.vw_cumulative_rent_growth AS growth
    ON kpi.observation_year = growth.observation_year
    AND kpi.market = growth.market
    AND kpi.unit_type = growth.unit_type;