import os
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt

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

lines = Path("data/raw/ons/cpi_annual_rate_D7G7.csv").read_text(encoding="utf-8").splitlines()
print(len(lines))

for line in lines[0:12] + lines[43:48] + lines[193:198] + lines[-3:]:
    print(line)

print(con.sql("""
    SELECT
    -- the three numbers to work out
        count(*) AS months_checked,
        -- every month that passes the WHERE below
        count(*) FILTER (WHERE CFMZ6IQ - cpi_annual_rate < 0) AS months_losing,
        -- only the months where existing easy access paid less than inflation
        round(avg(CFMZ6IQ - cpi_annual_rate), 2) AS avg_real_return
        -- the average of rate minus inflation over those months, in percentage points, to 2 decimals
    FROM mart.monthly_rates_cpi
    -- the table with savings rates and inflation in the same row
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- only the 128 complete months, January 2016 to August 2026
"""))
df = con.sql("SELECT month, CFMZ6IQ, cpi_annual_rate, CFMZ6IQ - cpi_annual_rate AS real_return FROM mart.monthly_rates_cpi WHERE month BETWEEN '2016-01-01' AND '2026-08-01' ORDER BY month").df()
print(df)




plt.plot(df["month"], df["CFMZ6IQ"], label="Existing easy access")
plt.plot(df["month"], df["cpi_annual_rate"], label = "inflation")
plt.plot(df["month"], df["real_return"], label = "real-return")
plt.axhline(0, color="black")
plt.legend()
plt.show()

plt.title("Existing easy access savers vs inflation, 2016 to 2026")
plt.ylabel("% a year")

Path("charts").mkdir(exist_ok=True)

plt.savefig("charts/real_return.png", dpi=150)
plt.show()
con.close()


print(con.sql("""
    SELECT
    -- four columns, one row per year
        year(month) AS year,
        -- the year each month belongs to
        count(*) AS months,
        -- how many months that year has in the window, 12 except 2026
        count(*) FILTER (WHERE CFMZ6IQ - cpi_annual_rate < 0) AS months_losing,
        -- how many of them savers earned less than inflation
        round(avg(CFMZ6IQ - cpi_annual_rate) * 100) AS real_pounds_per_10k
        -- that year's average real return in pounds on £10,000, negative is a loss
    FROM mart.monthly_rates_cpi
    -- the table with savings rates and inflation in the same row
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- the 128 complete months
    GROUP BY year
    -- one row per year
    ORDER BY year
    -- oldest year first
"""))
# finding 2, year by year