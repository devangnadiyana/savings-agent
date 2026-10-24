# Savings Agent

This is a project I'm building to work out how much money people in the UK lose by leaving their savings in low rate accounts. It's still a work in progress and I'm adding to it every day.

The bigger plan is a savings agent that tells people where their money should go and whether to fix now or wait. This repo is the data and modelling side of it.

## What I found so far

Between 2021 and 2023 Bank Rate went up from 0.1% to 5.25%. Banks passed that rise on to new 1 year fixed bonds, which got to about 5.5%, but people with money sitting in their existing easy access accounts were only earning about 1.8%. So if you kept £10,000 in easy access instead of a 1 year bond you lost about £304 in 2023 alone. Back in 2021 it was only £16.

## Where the data comes from

Everything is public and gets downloaded by the scripts. Bank Rate, savings rates and yield curves come from the Bank of England, along with their household survey. Inflation comes from the ONS and ISA numbers come from HMRC.

## How to run it

Install the libraries first

    pip install requests duckdb pandas matplotlib

Then run these in order

    python download_all.py
    python load_series.py
    python explore.py
    python chart_gap.py

The first one downloads around 137 MB of data, the second builds the database, the third checks the data and the last one draws the chart behind the finding above.

## Where it's at

Done so far is the data pipeline and the first finding. Next up is adjusting for inflation, measuring how fast banks pass on rate changes, and then the forecasting model.