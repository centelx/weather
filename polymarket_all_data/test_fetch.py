import os
import sys
import datetime
from fetch_hourly_snapshots import fetch_history_for_market, session

slug = 'highest-temperature-in-miami-on-june-15-2026'
target_dt = datetime.datetime.strptime('2026-06-15', '%Y-%m-%d').date()

df = fetch_history_for_market(slug, target_dt, 'MAX')
print(df)
