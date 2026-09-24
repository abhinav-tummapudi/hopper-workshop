#!/usr/bin/env python3
"""
load_csv.py — fallback loader if LOAD DATA LOCAL INFILE is blocked.

    python load_csv.py earthquakes.csv

Reads the raw USGS CSV with pandas, keeps the columns the schema wants, and
appends it to research_db.earthquakes over the local Unix socket. Slower
than LOAD DATA, but it always works and uses the same connection string the
Streamlit app uses.
"""
import os
import sys

import pandas as pd
from sqlalchemy import create_engine

SOCKET = os.environ.get("MARIADB_SOCKET", os.path.expanduser("~/my_database/mysql.sock"))
DB = os.environ.get("MARIADB_DB", "research_db")

if not DB_PASSWORD:
    raise SystemExit(
        "MARIADB_PASSWORD is not set. "
        "Run: export MARIADB_PASSWORD='<your-password>'"
    )

csv_path = sys.argv[1] if len(sys.argv) > 1 else "earthquakes.csv"

df = pd.read_csv(csv_path, parse_dates=["time", "updated"])

df = df.rename(columns={
    "time": "event_time",
    "depth": "depth_km",
    "mag": "magnitude",
    "magType": "mag_type",
    "type": "event_type",
})

keep = ["id", "event_time", "latitude", "longitude", "depth_km", "magnitude",
        "mag_type", "place", "event_type", "net", "status", "updated"]
df = df[keep]

engine = create_engine(f"mysql+pymysql://root@localhost/{DB}?unix_socket={SOCKET}")
df.to_sql("earthquakes", engine, if_exists="append", index=False, chunksize=1000)

print(f"Loaded {len(df):,} rows into {DB}.earthquakes")
