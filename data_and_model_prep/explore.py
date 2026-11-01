import os
# operating system functions, used to change folder
from pathlib import Path
# builds file paths
import duckdb
# the database library

os.chdir(Path(__file__).parent)
# move into the folder this script lives in, so data/ is found wherever VS Code runs from
con = duckdb.connect("data/warehouse.duckdb")
# open the warehouse

print(con.sql("SELECT * FROM read_csv('data/raw/boe/series/IUDBEDR.csv') LIMIT 5"))
# Reads the Bank Rate file straight from disk and prints its first 5 rows. Nothing is saved to the database.
# Under each column name, DuckDB prints the type it guessed for that column.

print(con.sql("""SELECT count(*) AS n_rows, max("DATE") AS latest_date FROM read_csv('data/raw/boe/series/IUDBEDR.csv')"""))
# Counts every row in the file, and asks for the "largest" value in the DATE column.
# The triple quotes """ let this text contain both kinds of quote mark: "DATE" (a column name) and '...' (a file path).

print(con.sql("""SELECT max(strptime("DATE", '%d %b %Y')::DATE) AS latest_date FROM read_csv('data/raw/boe/series/IUDBEDR.csv')"""))
# strptime(text, pattern) reads text as a date using the pattern you give it: %d = day number, %b = short month name, %Y = 4-digit year.
# '%d %b %Y' matches "16 Oct 2026": day, space, month, space, year.
# ::DATE turns the result into a real date, so max() now compares dates, not letters.

print(con.sql("SELECT max(obs_date) AS latest_date FROM staging.boe_series WHERE series_code = 'IUDBEDR'"))
# the latest day with a daily Bank Rate value, read from the long table

print(con.sql("SELECT max(x) AS biggest FROM (VALUES ('9'), ('10')) AS t(x)"))
# made up, the bigger of 9 and 10 stored as text. Delete after question 3
print(con.sql("SELECT max(x) AS biggest FROM (VALUES (9), (10)) AS t(x)"))
# made up, the same two values stored as numbers. Delete after question 3

print(con.sql("""
    SELECT
    -- one row per series, with these six columns
        series_code,
        -- the name of each series
        count(*)        AS n_rows,
        -- how many rows that series has
        min(obs_date)   AS first_date,
        -- its earliest date
        max(obs_date)   AS last_date,
        -- its latest date
        min(value)      AS lowest,
        -- its lowest value
        max(value)      AS highest
        -- its highest value
    FROM staging.boe_series
    -- the 15 series table
    GROUP BY series_code
    -- one pile per series, so each pile becomes one row
    ORDER BY first_date
    -- the series that starts earliest comes first
"""))
# check 1: the profile of every series

print(con.sql("""
    PIVOT (
    -- turns the long table into one row per date, one column per series
        SELECT obs_date, series_code, value
        -- the three columns of boe_series
        FROM staging.boe_series
        -- the long table
        WHERE series_code IN ('IUMABEDR', 'IUMWTFA', 'CFMZ6IQ')
        -- only Bank Rate (monthly average), the 1 year bond, and existing easy access
          AND obs_date IN ('2015-11-30', '2015-12-31', '2016-01-31', '2016-02-29', '2026-07-31', '2026-08-31', '2026-09-30')
        -- only seven month ends, around the start of 2016 and the latest few
    )
    -- end of the inner query
    ON series_code
    -- each series code becomes its own column
    USING first(value)
    -- the number that goes in each cell
    ORDER BY obs_date
    -- oldest date first
"""))
# check 2: shows the NULLs where a series has no value

print(con.sql("""
    SELECT
    -- three numbers about the complete months
        count(*)   AS complete_months,
        -- how many months pass the filter below
        min(month) AS first_complete,
        -- the earliest of those months
        max(month) AS last_complete
        -- the latest of those months
    FROM mart.monthly_rates
    -- the wide table, 622 months, one column per series
    WHERE COLUMNS(*) IS NOT NULL
    -- keeps only months where every column is filled in
"""))
# check 3: the 128 complete months

print(con.sql("""
    SELECT
    -- one row per year
        year(month) AS year,
        -- the year each month belongs to
        round(avg(IUMWTFA - CFMZ6IQ) * 100) AS pounds_lost_per_10k
        -- average gap between the new 1 year bond and existing easy access, in pounds on £10,000
    FROM mart.monthly_rates
    -- the wide table
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- the 128 complete months
    GROUP BY year
    -- one pile per year
    ORDER BY year
    -- oldest year first
"""))
# finding 1: pounds lost per £10,000 a year against a new 1 year bond

lines = Path("data/raw/ons/cpi_annual_rate_D7G7.csv").read_text(encoding="utf-8").splitlines()
# reads the raw inflation file as text and splits it into a list of lines
print(len(lines))
# how many lines the file has
for line in lines[0:12] + lines[43:48] + lines[193:198] + lines[-3:]:
    # four slices: the notes at the top, where yearly turns quarterly, where quarterly turns monthly, and the last three lines
    print(line)
    # prints each of those lines

print(con.sql("""
    SELECT
    -- three numbers for the whole window
        count(*) AS months_checked,
        -- every month that passes the WHERE below
        count(*) FILTER (WHERE CFMZ6IQ - cpi_annual_rate < 0) AS months_losing,
        -- only the months where existing easy access paid less than inflation
        round(avg(CFMZ6IQ - cpi_annual_rate), 2) AS avg_real_return
        -- average of rate minus inflation, in percentage points
    FROM mart.monthly_rates_cpi
    -- the table with savings rates and inflation in the same row
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- the 128 complete months
"""))
# finding 2: how often savers lost to inflation

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

con.close()
# closes the database file, last line