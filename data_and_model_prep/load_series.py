import os
# The standard library for working with the operating system, e.g. changing folders.
from pathlib import Path
# Path builds file locations.

os.chdir(Path(__file__).parent)
# Path(__file__).parent is the folder this script lives in. os.chdir moves into that folder before anything else runs,
# so "data/..." always points to your project's data folder, wherever the terminal happens to be.
import duckdb #its a database library

#opens the warehouse.duckdb file, if not present will create one
con = duckdb.connect("data/warehouse.duckdb")#one file where duckdb keeps all the tables together, con holds the result of connect()
#connect is 

print("connected")#confirmation'

con.execute("CREATE SCHEMA IF NOT EXISTS staging")

print(con.execute("SELECT schema_name FROM information_schema.schemata WHERE catalog_name = current_database()").fetchall()) 
print(con.sql("SELECT * FROM read_csv('data/raw/boe/series/IUDBEDR.csv') LIMIT 5"))
# Reads the Bank Rate file straight from disk and prints its first 5 rows. Nothing is saved to the database yet.
# Under each column name, DuckDB prints the type it guessed for that column.
#main and staging: a schema is a named group of tables inside the database. main is the one every DuckDB database 
# starts with. staging is the one you made, to hold the cleaned copies of your files.
print(con.sql("""SELECT count(*) AS n_rows, max("DATE") AS latest_date FROM read_csv('data/raw/boe/series/IUDBEDR.csv')"""))
# Counts every row in the file, and asks for the "largest" value in the DATE column.
# The triple quotes """ let this text contain both kinds of quote mark: "DATE" (a column name) and '...' (a file path).

#dates are in varchar so needs to be turned to date type

print(con.sql("""SELECT max(strptime("DATE", '%d %b %Y')::DATE) AS latest_date FROM read_csv('data/raw/boe/series/IUDBEDR.csv')"""))
# strptime(text, pattern) reads text as a date using the pattern you give it: %d = day number, %b = short month name, %Y = 4-digit year.
# '%d %b %Y' matches "16 Oct 2026": day, space, month, space, year.
# ::DATE turns the result into a real date, so max() now compares dates, not letters.

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
print(con.sql("DESCRIBE staging.bank_rate"))
# Shows the new table's columns and their types.


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
print(con.sql("SELECT count(*) AS n_rows, count(DISTINCT series_code) AS n_series FROM staging.boe_series"))
# Counts all the rows, and how many different series codes there are.
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