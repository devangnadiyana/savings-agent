import os
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt

os.chdir(Path(__file__).parent)#working from the parent folder
con = duckdb.connect("data/warehouse.duckdb")#open database

rates = con.sql("""
                SELECT month, IUDBEDR, IUMWTFA, IUMB6VJ, CFMZ6IQ
                FROM mart.monthly_rates
                WHERE month BETWEEN '2016-01-01' AND '2026-08-01'
                ORDER BY month
""").df()
#four columns from that wide merged table, for 128 months as a panda table
## IUDBEDR = Bank Rate, IUMWTFA = advertised 1-year bond, IUMB6VJ = advertised easy access,
# CFMZ6IQ = what people actually earn on money already in easy-access accounts

plt.plot(rates["month"], rates["IUDBEDR"], label="Bank Rate")
# One line for Bank Rate. 'label' is the name that appears in the key.
plt.plot(rates["month"], rates["IUMWTFA"], label="Advertised: 1-year fixed bond")
# A line for the rate banks advertise on a new 1-year bond.
plt.plot(rates["month"], rates["IUMB6VJ"], label="Advertised: easy access")
# A line for the rate banks advertise on a new easy-access account.
plt.plot(rates["month"], rates["CFMZ6IQ"], label="Actually earned: easy access")
# A line for what people really earn on easy-access money they already hold.
plt.title("What savers could earn vs what they did earn, 2016-2026")

plt.ylabel("%")
plt.legend()
plt.savefig("data/rates_gap.png", dpi=150)
# Saves the chart as an image in your data folder.
plt.show()
# Opens the chart window; close it to let the script finish.
con.close()