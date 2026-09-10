"""AQPL Maintenance Dashboard entrypoint.

Stability-first entrypoint: keep the proven dashboard in ``legacy_app.py`` and
add only small, targeted mobile-friendly helpers here.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


# Mobile-friendly rendering for the Home tab's Today / Upcoming PM table.
# The legacy dashboard passes a dataframe containing a Status column with
# DUE TODAY / UPCOMING values.  On narrow portrait screens the first rows can
# be easy to miss inside Streamlit's scrollable dataframe, so due-today jobs
# are rendered as simple cards with the date first and upcoming jobs remain in
# a normal dataframe.  Other dataframes are untouched.
_ORIGINAL_DATAFRAME = st.dataframe


def _mobile_friendly_dataframe(data=None, *args, **kwargs):
    try:
        is_pm_home_table = (
            isinstance(data, pd.DataFrame)
            and "Status" in data.columns
            and "scheduled_date" in data.columns
            and data["Status"].astype(str).isin(["DUE TODAY", "UPCOMING"]).any()
        )
    except Exception:
        is_pm_home_table = False

    if not is_pm_home_table:
        return _ORIGINAL_DATAFRAME(data, *args, **kwargs)

    frame = data.copy()
    due = frame[frame["Status"].astype(str) == "DUE TODAY"].copy()
    upcoming = frame[frame["Status"].astype(str) == "UPCOMING"].copy()

    if not due.empty:
        st.markdown("#### 🔴 Due Today")
        for _, row in due.iterrows():
            raw_date = row.get("scheduled_date", "")
            try:
                date_text = pd.to_datetime(raw_date).strftime("%d %b %Y")
            except Exception:
                date_text = str(raw_date)

            name = ""
            for col in ["machine_name", "Machine Name", "machine", "Machine"]:
                if col in due.columns and pd.notna(row.get(col)):
                    name = str(row.get(col)).strip()
                    if name:
                        break

            code = ""
            for col in ["machine_code", "Machine Code", "code", "Code"]:
                if col in due.columns and pd.notna(row.get(col)):
                    code = str(row.get(col)).strip()
                    if code:
                        break

            frequency = ""
            for col in ["frequency", "Frequency"]:
                if col in due.columns and pd.notna(row.get(col)):
                    frequency = str(row.get(col)).strip()
                    if frequency:
                        break

            title = f"📅 {date_text}"
            if name:
                title += f" — {name}"
            details = " · ".join(x for x in [code, frequency] if x)
            if details:
                st.markdown(f"**{title}**  \n{details}")
            else:
                st.markdown(f"**{title}**")

    if upcoming.empty:
        return None

    st.markdown("#### 📆 Upcoming")
    preferred = [c for c in ["scheduled_date", "machine_name", "machine_code", "frequency", "Status"] if c in upcoming.columns]
    remaining = [c for c in upcoming.columns if c not in preferred]
    upcoming = upcoming[preferred + remaining]
    return _ORIGINAL_DATAFRAME(upcoming, *args, **kwargs)


st.dataframe = _mobile_friendly_dataframe

# Load the full maintenance dashboard.
from legacy_app import *  # noqa: F401,F403,E402


# Restore the native dataframe function after legacy_app has rendered so later
# helpers do not unexpectedly inherit the targeted Home-tab behavior.
st.dataframe = _ORIGINAL_DATAFRAME


def _render_breakdown_hours_sidebar():
    """Show current/month-wise BM downtime without modifying the main tab system."""
    try:
        bm = q(
            "select job_id,machine_code,machine_name,opened_at,closed_at,status "
            "from jobs where job_type='BM'"
        )
    except Exception as exc:
        with st.sidebar.expander("⏱️ Breakdown Hours", expanded=False):
            st.warning(f"Summary load nahi ho saka: {exc}")
        return

    with st.sidebar.expander("⏱️ Breakdown Hours", expanded=False):
        st.caption("Start Time aur End Time se downtime automatically calculate hota hai.")

        if bm.empty:
            st.info("Abhi koi saved Breakdown Maintenance record available nahi hai.")
            return

        bm = bm.copy()
        bm["opened_at"] = pd.to_datetime(bm["opened_at"], errors="coerce")
        bm["closed_at"] = pd.to_datetime(bm["closed_at"], errors="coerce")
        bm = bm[bm["opened_at"].notna() & bm["closed_at"].notna()].copy()

        if bm.empty:
            st.info("Valid Start Time / End Time wale closed breakdown records available nahi hain.")
            return

        bm["breakdown_hours"] = (
            (bm["closed_at"] - bm["opened_at"]).dt.total_seconds() / 3600.0
        )
        bm = bm[bm["breakdown_hours"] >= 0].copy()

        if bm.empty:
            st.info("Valid breakdown duration available nahi hai.")
            return

        bm["month_key"] = bm["opened_at"].dt.strftime("%Y-%m")
        monthly = (
            bm.groupby("month_key", as_index=False)
            .agg(
                breakdown_hours=("breakdown_hours", "sum"),
                breakdown_jobs=("job_id", "nunique"),
            )
            .sort_values("month_key", ascending=False)
        )

        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        current_key = now.strftime("%Y-%m")
        current_rows = bm[bm["month_key"] == current_key]
        current_hours = float(current_rows["breakdown_hours"].sum())
        current_jobs = int(current_rows["job_id"].nunique())

        st.metric(f"{now.strftime('%B %Y')} Breakdown", f"{current_hours:.2f} hr")
        st.caption(f"Current month closed breakdown jobs: {current_jobs}")

        month_options = monthly["month_key"].tolist()
        default_index = month_options.index(current_key) if current_key in month_options else 0
        selected_month = st.selectbox(
            "Check Month",
            month_options,
            index=default_index,
            format_func=lambda value: pd.to_datetime(value + "-01").strftime("%B %Y"),
            key="stable_breakdown_month_filter",
        )

        selected = monthly[monthly["month_key"] == selected_month].iloc[0]
        st.metric("Selected Month Hours", f"{float(selected['breakdown_hours']):.2f} hr")
        st.caption(f"Breakdown jobs: {int(selected['breakdown_jobs'])}")

        recent = monthly.head(6).copy()
        recent["Month"] = pd.to_datetime(recent["month_key"] + "-01").dt.strftime("%b %Y")
        recent["Hours"] = recent["breakdown_hours"].round(2)
        recent["Jobs"] = recent["breakdown_jobs"].astype(int)
        st.markdown("**Last 6 Months**")
        st.dataframe(
            recent[["Month", "Hours", "Jobs"]],
            use_container_width=True,
            hide_index=True,
        )


_render_breakdown_hours_sidebar()
