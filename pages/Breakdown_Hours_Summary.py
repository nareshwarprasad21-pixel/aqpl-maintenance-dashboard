import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import sqlite3
import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None

st.set_page_config(page_title="Breakdown Hours Summary", page_icon="⏱️", layout="wide")

BASE = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(BASE, "data", "maintenance.db")
IST = ZoneInfo("Asia/Kolkata")


def _secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return str(os.getenv(name, "")).strip()


def load_breakdown_jobs():
    supabase_url = _secret("SUPABASE_URL")
    supabase_key = _secret("SUPABASE_SECRET_KEY") or _secret("SUPABASE_SERVICE_ROLE_KEY")

    if create_client and supabase_url and supabase_key:
        sb = create_client(supabase_url, supabase_key)
        rows = (
            sb.table("jobs")
            .select("job_id,machine_code,machine_name,location,opened_at,closed_at,status")
            .eq("job_type", "BM")
            .execute()
            .data
            or []
        )
        return pd.DataFrame(rows)

    if os.path.exists(DB):
        with sqlite3.connect(DB) as con:
            return pd.read_sql_query(
                """
                select job_id,machine_code,machine_name,location,opened_at,closed_at,status
                from jobs
                where job_type='BM'
                """,
                con,
            )

    return pd.DataFrame()


st.title("⏱️ Breakdown Hours Summary")
st.caption("Saved Breakdown Maintenance records ke Start Time aur End Time se month-wise breakdown hours automatically calculate hote hain.")

df = load_breakdown_jobs()

if df.empty:
    st.info("Abhi koi saved Breakdown Maintenance record available nahi hai.")
    st.stop()

for col in ["opened_at", "closed_at"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

df = df[df["opened_at"].notna() & df["closed_at"].notna()].copy()

if df.empty:
    st.info("Saved breakdown records me valid Start Time aur End Time available nahi hai.")
    st.stop()

df["breakdown_hours"] = (df["closed_at"] - df["opened_at"]).dt.total_seconds() / 3600
# Ignore invalid negative durations if an old record contains incorrect timing.
df = df[df["breakdown_hours"] >= 0].copy()
df["month_key"] = df["opened_at"].dt.to_period("M").astype(str)
df["month_label"] = df["opened_at"].dt.strftime("%b %Y")

now = datetime.now(IST)
current_month_key = now.strftime("%Y-%m")
current_month_label = now.strftime("%b %Y")

monthly = (
    df.groupby("month_key", as_index=False)
    .agg(breakdown_hours=("breakdown_hours", "sum"), breakdown_jobs=("job_id", "nunique"))
    .sort_values("month_key")
)
monthly["month_label"] = pd.to_datetime(monthly["month_key"] + "-01").dt.strftime("%b %Y")

current_rows = df[df["month_key"] == current_month_key]
current_hours = current_rows["breakdown_hours"].sum()
current_jobs = current_rows["job_id"].nunique()

month_options = monthly.sort_values("month_key", ascending=False)["month_key"].tolist()
default_month = current_month_key if current_month_key in month_options else month_options[0]
selected_month = st.selectbox(
    "Month Filter",
    options=month_options,
    index=month_options.index(default_month),
    format_func=lambda x: pd.to_datetime(x + "-01").strftime("%B %Y"),
)
selected_rows = df[df["month_key"] == selected_month].copy()
selected_hours = selected_rows["breakdown_hours"].sum()
selected_jobs = selected_rows["job_id"].nunique()
selected_label = pd.to_datetime(selected_month + "-01").strftime("%B %Y")

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"Current Month Breakdown Hours ({current_month_label})", f"{current_hours:.2f} hr")
m2.metric("Current Month Breakdown Jobs", f"{current_jobs}")
m3.metric(f"Selected Month Hours ({selected_label})", f"{selected_hours:.2f} hr")
m4.metric("Selected Month Breakdown Jobs", f"{selected_jobs}")

st.markdown("### 📈 Month-wise Breakdown Hours Trend")
trend = monthly[["month_label", "breakdown_hours"]].set_index("month_label")
st.line_chart(trend, y="breakdown_hours", use_container_width=True)

st.markdown(f"### 📋 {selected_label} Breakdown Details")
show_cols = ["job_id", "machine_code", "machine_name", "location", "opened_at", "closed_at", "breakdown_hours", "status"]
selected_rows = selected_rows.sort_values("opened_at", ascending=False)
selected_rows["breakdown_hours"] = selected_rows["breakdown_hours"].round(2)
st.dataframe(selected_rows[show_cols], use_container_width=True, hide_index=True)

st.caption("Note: Breakdown month Start Date/Time ke basis par assign hota hai. Hours saved Start Time aur End Time ke difference se calculate hote hain.")