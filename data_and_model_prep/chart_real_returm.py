import os
# operating system functions, used to change folder
from pathlib import Path
# builds file and folder paths
import duckdb
# the database library
import matplotlib.pyplot as plt
# the plotting library, plt is the usual short name

os.chdir(Path(__file__).parent)
# move into the folder this script lives in, so data/ and charts/ are found wherever VS Code runs from
con = duckdb.connect("data/warehouse.duckdb")
# open the warehouse

df = con.sql("""
    SELECT
    -- the four columns the chart needs
        month,
        -- the month, goes along the bottom
        CFMZ6IQ,
        -- what existing easy access savers earned that month
        cpi_annual_rate,
        -- inflation that month
        CFMZ6IQ - cpi_annual_rate AS real_return
        -- savers' rate minus inflation, below zero means lost buying power
    FROM mart.monthly_rates_cpi
    -- the table with savings rates and inflation in the same row
    WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
    -- the 128 complete months
    ORDER BY month
    -- oldest first, so the lines draw left to right
""").df()
# runs the query in DuckDB, and .df() turns the result into a pandas table called df
con.close()
# the data is now in df, so the database can be closed

plt.plot(df["month"], df["CFMZ6IQ"], label="Existing easy access")
# line 1: what savers earned each month
plt.plot(df["month"], df["cpi_annual_rate"], label="Inflation")
# line 2: inflation each month
plt.plot(df["month"], df["real_return"], label="Real return")
# line 3: the difference, below zero means savers lost buying power that month
plt.axhline(0, color="black")
# a flat black line at 0, so months below zero are easy to see
plt.legend()
# the box matching each colour to its label
plt.title("Existing easy access savers vs inflation, 2016 to 2026")
# the name of the chart, at the top
plt.ylabel("% a year")
# what the numbers up the side are
Path("charts").mkdir(exist_ok=True)
# makes the charts folder if it is missing, no error if it is already there
plt.savefig("charts/real_return.png", dpi=150)
# saves the picture, it must come before show
plt.show()
# opens the window, and the script waits here until you close it