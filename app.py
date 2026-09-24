"""
app.py — Streamlit dashboard over the MariaDB instance running on Hopper,
serving the USGS earthquake dataset.

Run it on the SAME node where mariadbd-safe is running (the Unix socket is
node-local, even though $HOME is shared storage):

    streamlit run app.py --server.port 8501 --server.address 0.0.0.0 \
        --server.headless true

Then, from your laptop:

    ssh -N -L 8501:<node-name>:8501 <NetID>@hopper.orc.gmu.edu

and open http://localhost:8501
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------
SOCKET = os.environ.get(
    "MARIADB_SOCKET", os.path.expanduser("~/my_database/mysql.sock")
)
DB = os.environ.get("MARIADB_DB", "research_db")
DB_USER = os.environ.get("MARIADB_USER", "streamlit_user")
DB_PASSWORD = os.environ.get("MARIADB_PASSWORD")

st.set_page_config(page_title="Earthquake Explorer", layout="wide")


@st.cache_resource
def get_engine():
    # MariaDB and Streamlit must run on the same Hopper node.
    if not DB_PASSWORD:
        raise RuntimeError(
            "MARIADB_PASSWORD is not set. "
            "Run: export MARIADB_PASSWORD='<your-password>'"
        )
    return create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@localhost/{DB}?unix_socket={SOCKET}",
        pool_pre_ping=True,
    )


@st.cache_data(ttl=300)
def load_events() -> pd.DataFrame:
    query = """
        SELECT id, event_time, latitude, longitude, depth_km, magnitude,
               mag_type, place, event_type, net, status
        FROM earthquakes
    """
    df = pd.read_sql(query, get_engine())
    df["event_time"] = pd.to_datetime(df["event_time"])
    df["date"] = df["event_time"].dt.date
    return df


st.title("Earthquake Explorer")
st.caption("USGS earthquake catalog records served from MariaDB running on Hopper")

try:
    events = load_events()
except Exception as exc:  # noqa: BLE001
    st.error(
        "Could not reach MariaDB. Check that mariadbd-safe is running on this "
        f"node and that the socket path is correct.\n\nSocket: `{SOCKET}`"
    )
    st.exception(exc)
    st.stop()

# --------------------------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------------------------
st.sidebar.header("Filters")

mag_min = float(events["magnitude"].min())
mag_max = float(events["magnitude"].max())
mag_range = st.sidebar.slider("Magnitude", mag_min, mag_max, (mag_min, mag_max))

types = sorted(events["event_type"].dropna().unique())
chosen_types = st.sidebar.multiselect("Event type", types, default=types)

min_d, max_d = events["date"].min(), events["date"].max()
date_range = st.sidebar.date_input("Between", (min_d, max_d),
                                   min_value=min_d, max_value=max_d)

df = events[
    events["magnitude"].between(mag_range[0], mag_range[1])
    & events["event_type"].isin(chosen_types)
]
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    df = df[(df["date"] >= date_range[0]) & (df["date"] <= date_range[1])]

if df.empty:
    st.warning("No events match the current filters.")
    st.stop()

# --------------------------------------------------------------------------
# Headline numbers
# --------------------------------------------------------------------------
biggest = df.loc[df["magnitude"].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Events", f"{len(df):,}")
c2.metric("Average magnitude", f"{df['magnitude'].mean():.2f}")
c3.metric("Largest magnitude", f"{biggest['magnitude']:.1f}")
c4.metric("Date range", f"{(df['date'].max() - df['date'].min()).days} days")
st.caption(f"Largest event: M{biggest['magnitude']:.1f} — {biggest['place']}")

st.divider()

# --------------------------------------------------------------------------
# Map
# --------------------------------------------------------------------------
st.subheader("Epicenters")
fig = px.scatter_geo(
    df, lat="latitude", lon="longitude",
    size=df["magnitude"].clip(lower=0.1),
    color="magnitude",
    color_continuous_scale="YlOrRd",
    hover_name="place",
    hover_data={"magnitude": True, "depth_km": True, "latitude": False,
                "longitude": False},
    projection="natural earth",
)
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=420)
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Magnitude distribution")
    fig = px.histogram(df, x="magnitude", nbins=30)
    fig.update_traces(marker_color="#1E5C3A")
    fig.update_layout(yaxis_title="Events")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Events per day")
    daily = df.groupby("date", as_index=False).size()
    fig = px.line(daily, x="date", y="size",
                  labels={"date": "Date", "size": "Events"})
    fig.update_traces(line_color="#1E5C3A")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Depth vs. magnitude")
    fig = px.scatter(df, x="depth_km", y="magnitude", opacity=0.5,
                     labels={"depth_km": "Depth (km)", "magnitude": "Magnitude"})
    fig.update_traces(marker_color="#1E5C3A")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Events by network")
    by_net = df.groupby("net", as_index=False).size().sort_values(
        "size", ascending=False).head(10)
    fig = px.bar(by_net, x="net", y="size",
                labels={"net": "Reporting network", "size": "Events"})
    fig.update_traces(marker_color="#F0A500")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Largest earthquakes in view")
top = (
    df.sort_values("magnitude", ascending=False)
    .head(10)[["event_time", "magnitude", "depth_km", "place"]]
)
st.dataframe(top, use_container_width=True, hide_index=True)

with st.expander("Show raw rows"):
    st.dataframe(df.head(500), use_container_width=True, hide_index=True)
