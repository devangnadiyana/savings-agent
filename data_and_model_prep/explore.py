import os
from pathlib import Path
import duckdb

os.chdir(Path(__file__).parent)
con = duckdb.connect("data/warehouse.duckdb")

print(con.sql("""
    SELECT
        series_code,
        -- The name of each series (one row per series, because of GROUP BY below).
        count(*)        AS n_rows,
        -- How many rows that series has.
        min(obs_date)   AS first_date,
        -- Its earliest date.
        max(obs_date)   AS last_date,
        -- Its latest date.
        min(value)      AS lowest,
        -- Its lowest value.
        max(value)      AS highest
        -- Its highest value.
    FROM staging.boe_series
    -- Read from your 15-series table.
    GROUP BY series_code
    -- One pile per series, so each pile becomes one row.
    ORDER BY first_date
    -- Show the series that starts earliest first.
"""))

print(con.sql("""
    PIVOT (
    -- PIVOT turns the long table (one row per value) into a side-by-side table: one row per date, one column per series.
        SELECT obs_date, series_code, value
        -- Start from the three columns of your boe_series table.
        FROM staging.boe_series
        WHERE series_code IN ('IUMABEDR', 'IUMWTFA', 'CFMZ6IQ')
        -- Keep only three series: Bank Rate (monthly average), the 1-year bond rate, and the rate people actually earn on easy-access money.
          AND obs_date IN ('2015-11-30', '2015-12-31', '2016-01-31', '2016-02-29', '2026-07-31', '2026-08-31', '2026-09-30')
        -- Keep only seven month-ends: some around the start of 2016, and the latest few. That keeps the output small.
    )
    ON series_code
    -- Each series code becomes its own column.
    USING first(value)
    -- The number that goes into each cell.
    ORDER BY obs_date
    -- Oldest date first.
"""))

print(con.sql("""
    SELECT
        count(*)   AS complete_months,
        -- How many months pass the filter below.
        min(month) AS first_complete,
        -- The earliest of those months.
        max(month) AS last_complete
        -- The latest of those months.
    FROM mart.monthly_rates
    -- Your wide table: 622 months, with a column for each of the 15 rates.
    WHERE COLUMNS(*) IS NOT NULL
    -- COLUMNS(*) means "every column". This keeps only the months where no column is NULL, meaning all 15 rates are filled in.
"""))

print(con.sql("""
    SELECT
        year(month) AS year,
        -- The year each month belongs to, e.g. 2023-08-01 → 2023.
        round(avg(IUMWTFA - CFMZ6IQ) * 100) AS pounds_lost_per_10k
        -- For each year: the average gap between the bond rate and the rate actually earned, in pounds on £10,000.
    FROM mart.monthly_rates
    -- Your wide table.
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- Only the 128 complete months.
    GROUP BY year
    -- One pile per year, so one row per year.
    ORDER BY year
    -- Oldest year first.
"""))

