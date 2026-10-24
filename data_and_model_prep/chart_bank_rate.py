import os
from pathlib import Path
import duckdb
import matplotlib.pyplot as plt
# matplotlib is the charting library. pyplot is the part that draws charts, and 'plt' is the short name everyone uses for it.

os.chdir(Path(__file__).parent)

con = duckdb.connect("data/warehouse.duckdb")

bank_rate = con.sql("SELECT obs_date, value FROM staging.boe_series WHERE series_code = 'IUDBEDR' ORDER BY obs_date").df()
print(bank_rate)

plt.plot(bank_rate["obs_date"], bank_rate["value"])
# Draws a line: dates along the bottom (the x-axis), Bank Rate up the side (the y-axis).
# bank_rate["obs_date"] means "the obs_date column of the bank_rate table"; the same goes for "value".

plt.title("UK Bank Rate, 1975-2026")
# The title printed above the chart.

plt.ylabel("%")
# The label on the side axis, so people know the numbers are percentages.

plt.savefig("data/bank_rate.png", dpi=150)
# Saves the chart as an image in your data folder. dpi=150 sets the sharpness.

plt.show()
# Opens a window showing the chart. The script waits until you close the window.