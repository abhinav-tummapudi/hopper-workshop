#!/usr/bin/env python3
"""
download_earthquakes.py
------------------------
Downloads real earthquake records from the USGS Earthquake Catalog — a public
domain dataset, no API key, no account, no license to accept. Run this on
your LAPTOP; the resulting CSV is what you move to Hopper with Globus.

    python download_earthquakes.py                     # last 90 days, M2.5+
    python download_earthquakes.py --min-mag 4.0        # fewer, bigger quakes
    python download_earthquakes.py --days 365           # a full year

Source: USGS FDSN Event Web Service (https://earthquake.usgs.gov/fdsnws/event/1/)
License: Public domain (U.S. Geological Survey)

Only the Python standard library is required.
"""

import argparse
import csv
import io
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90,
                     help="how many trailing days to fetch (default 90)")
    ap.add_argument("--min-mag", type=float, default=2.5,
                     help="minimum magnitude (default 2.5)")
    ap.add_argument("--out", default="earthquakes.csv")
    args = ap.parse_args()

    end = datetime.utcnow()
    start = end - timedelta(days=args.days)

    params = {
        "format": "csv",
        "starttime": start.strftime("%Y-%m-%d"),
        "endtime": end.strftime("%Y-%m-%d"),
        "minmagnitude": args.min_mag,
        "orderby": "time",
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    print(f"Requesting {url}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw = resp.read().decode("utf-8")

    rows = list(csv.reader(io.StringIO(raw)))
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerows(rows)

    print(f"Wrote {len(rows) - 1:,} earthquakes ({start:%Y-%m-%d} to "
          f"{end:%Y-%m-%d}, M{args.min_mag}+) to {args.out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Download failed: {exc}", file=sys.stderr)
        print("Check your network connection, or fetch the URL above "
              "directly in a browser and save it as earthquakes.csv.",
              file=sys.stderr)
        sys.exit(1)
