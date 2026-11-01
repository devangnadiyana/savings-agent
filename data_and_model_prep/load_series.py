import os
# the standard library for working with the operating system, here used to change folder
from pathlib import Path
# Path builds file locations
import duckdb
# the database library

os.chdir(Path(__file__).parent)
# Path(__file__).parent is the folder this script lives in. os.chdir moves into that folder before anything else runs,
# so "data/..." always points to your project's data folder, wherever the terminal happens to be.

con = duckdb.connect("data/warehouse.duckdb")
# opens the warehouse file, or creates it if it isn't there. con is the open connection every query below uses
print("connected")
# confirms the connection opened

con.execute("CREATE SCHEMA IF NOT EXISTS staging")
# makes the staging folder if it doesn't exist yet, for cleaned copies of the raw files

con.execute("""
    CREATE OR REPLACE TABLE staging.bank_rate AS
    -- Makes a table called bank_rate inside the staging schema, filled with the result of the SELECT below. OR REPLACE rebuilds it on every run.
    SELECT
        strptime("DATE", '%d %b %Y')::DATE AS obs_date,
        -- Converts the text date into a real date and names the column obs_date.
        CAST("IUDBEDR" AS DECIMAL(9, 4)) AS bank_rate
        -- Converts the rate into an exact decimal (up to 4 decimal places) and names the column bank_rate.
    FROM read_csv('data/raw/boe/series/IUDBEDR.csv', header = true, all_varchar = true)
    -- header = true: the first line holds column names. all_varchar = true: read everything as text, so DuckDB guesses nothing and we convert it ourselves.
""")
# builds staging.bank_rate, an old second copy of daily Bank Rate that D1 T4 removes

con.execute("""
    CREATE OR REPLACE TABLE staging.boe_series AS
    -- Makes a table called boe_series in staging from the SELECT below; rebuilt on every run.
    SELECT
        parse_filename(filename, true) AS series_code,
        -- Takes each row's file path, e.g. data/raw/boe/series/IUDBEDR.csv, and keeps just the name without .csv: IUDBEDR.
        strptime(obs_date, '%d %b %Y')::DATE AS obs_date,
        -- The same date conversion as Task 6.
        CAST(value AS DECIMAL(9, 4)) AS value
        -- The same number conversion as Task 6.
    FROM read_csv('data/raw/boe/series/*.csv', header = true, names = ['obs_date', 'value'], all_varchar = true, filename = true)
    -- *.csv means "every CSV file in this folder", so all 15 are read at once.
    -- names = [...]: each file calls its second column something different (IUDBEDR, IUMWTFA...), so every file gets the same two names. That's what lets them stack.
    -- filename = true adds a column holding the path of the file each row came from.
""")
# builds staging.boe_series, all 15 series stacked long
print(con.sql("SELECT count(*) AS n_rows, count(DISTINCT series_code) AS n_series FROM staging.boe_series"))
# Counts all the rows, and how many different series codes there are.

con.execute("""
    CREATE OR REPLACE TABLE staging.boe_monthly AS
    SELECT
        series_code,
        date_trunc('month', obs_date)::DATE AS month,
        CAST(avg(value) AS DECIMAL(9, 4)) AS value
    FROM staging.boe_series
    GROUP BY series_code, month
""")
# runs the SQL above on the open database connection
# CREATE OR REPLACE TABLE builds staging.boe_monthly from the SELECT, replacing any old copy
# SELECT starts the list of columns the new table will have
# series_code keeps which series each row belongs to
# date_trunc moves each date to the 1st of its month, ::DATE keeps it a plain date, AS month names it
# avg averages each pile, CAST keeps it exact to 4 decimal places, AS value names it
# FROM reads the long table staging.boe_series
# GROUP BY makes one pile per series per month, so avg works pile by pile
print(con.sql("SELECT count(*) AS n_rows FROM staging.boe_monthly"))
# counts the rows of the monthly table

con.execute("CREATE SCHEMA IF NOT EXISTS mart")
# A second schema called 'mart', for finished tables that are ready for analysis and models.
# 'staging' holds cleaned copies of the raw files; 'mart' holds what you build from them.

con.execute("""
    CREATE OR REPLACE TABLE mart.monthly_rates AS
    -- Saves the result as a table called monthly_rates in the mart schema; rebuilt on every run.
    PIVOT staging.boe_monthly
    -- Start from your monthly table, which has one row per series per month (long format).
    ON series_code
    -- Every series code becomes its own column: IUDBEDR, IUMWTFA, CFMZ6IQ and so on, 15 columns in all.
    USING first(value)
    -- The number that goes in each cell. There's only one value per series per month, so 'first' simply takes it.
    ORDER BY month
    -- Oldest month first.
""")
# 'month' is the only column that isn't used in ON or USING, so PIVOT makes one row per month automatically.
print(con.sql("SELECT count(*) AS n_months, min(month) AS first_month, max(month) AS last_month FROM mart.monthly_rates"))
# How many months the table has, and its first and last month.

con.execute("""
    CREATE OR REPLACE TABLE staging.cpi AS
    -- makes the table staging.cpi, replacing it if it already exists
    SELECT
        strptime(period, '%Y %b')::DATE AS month,
        -- turns text like '1989 JAN' into a real date, 1989-01-01. %Y is the year, %b the month name
        CAST(value AS DECIMAL(9, 4)) AS cpi_annual_rate
        -- turns text like '4.9' into an exact number
    FROM read_csv('data/raw/ons/cpi_annual_rate_D7G7.csv', header = false, names = ['period', 'value'], all_varchar = true)
    -- reads the raw file: no header row, columns called period and value, everything kept as text
    WHERE length(period) = 8
    -- keeps only the monthly lines
""")
# runs the SQL above; it builds the table and prints nothing
print(con.sql("SELECT count(*) AS n_months, min(month) AS first_month, max(month) AS last_month FROM staging.cpi"))
# counts the months and shows the first and last, to check the load worked

con.execute("""
    CREATE OR REPLACE TABLE mart.monthly_rates_cpi AS
    -- makes the table mart.monthly_rates_cpi, replacing it if it already exists
    SELECT *
    -- every column from both tables
    FROM mart.monthly_rates LEFT JOIN staging.cpi USING (month)
    -- keeps all 622 months and adds inflation to the months that have it, matching on month
    ORDER BY month
    -- oldest month first
""")
# builds the table that holds savings rates and inflation in the same row
print(con.sql("SELECT count(*) AS n_months, count(cpi_annual_rate) AS months_with_cpi FROM mart.monthly_rates_cpi"))
# all months, and how many of them have an inflation value

con.close()
# closes the warehouse, always the last line