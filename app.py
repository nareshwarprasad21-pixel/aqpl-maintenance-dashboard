"""AQPL Maintenance Dashboard entrypoint.

The original dashboard is kept in ``legacy_app.py``.  This thin entrypoint
adds the Breakdown Hours Summary inside the existing Breakdown History tab
without changing the rest of the proven dashboard workflow.
"""

import inspect
import importlib
import streamlit as st


_ORIGINAL_TABS = st.tabs


def _render_breakdown_hours_summary(app_globals):
    """Render month-wise BM downtime summary using the dashboard's live jobs data."""
    q = app_globals.get("q")
    pd = app_globals.get("pd")
    datetime = app_globals.get("datetime")
    ZoneInfo = app_globals.get("ZoneInfo")

    if not all([q, pd, datetime, ZoneInfo]):
        return

    st.markdown("### ⏱️ Breakdown Hours Summary")
    st.caption(
        "Saved Breakdown Maintenance records ke Start Time aur End Time se "
        "breakdown hours automatically calculate hote hain."
    )

    try:
        bm = q(
            "select job_id,machine_code,machine_name,location,opened_at,closed_at,status "
            "from jobs where job_type='BM'"
        )
    except Exception as exc:
        st.warning(f"Breakdown summary load nahi ho saka: {exc}")
        st.markdown("---")
        return

    if bm.empty:
        st.info("Abhi koi saved Breakdown Maintenance record available nahi hai.")
        st.markdown("---")
        return

    for col in ["opened_at", "closed_at"]:
        bm[col] = pd.to_datetime(bm[col], errors="coerce")

    bm = bm[bm["opened_at"].notna() & bm["closed_at"].notna()].copy()
    if bm.empty:
        st.info("Saved breakdown records me valid Start Time aur End Time available nahi hai.")
        st.markdown("---")
        return

    bm["breakdown_hours"] = (
        (bm["closed_at"] - bm["opened_at"]).dt.total_seconds() / 3600
    )
    bm = bm[bm["breakdown_hours"] >= 0].copy()
    if bm.empty:
        st.info("Valid breakdown duration available nahi hai.")
        st.markdown("---")
        return

    bm["month_key"] = bm["opened_at"].dt.to_period("M").astype(str)
    monthly = (
        bm.groupby("month_key", as_index=False)
        .agg(
            breakdown_hours=("breakdown_hours", "sum"),
            breakdown_jobs=("job_id", "nunique"),
        )
        .sort_values("month_key")
    )
    monthly["month_label"] = pd.to_datetime(
        monthly["month_key"] + "-01"
    ).dt.strftime("%b %Y")

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_key = now.strftime("%Y-%m")
    current_label = now.strftime("%B %Y")
    current_rows = bm[bm["month_key"] == current_key]
    current_hours = float(current_rows["breakdown_hours"].sum())
    current_jobs = int(current_rows["job_id"].nunique())

    month_options = monthly.sort_values("month_key", ascending=False)["month_key"].tolist()
    default_month = current_key if current_key in month_options else month_options[0]
    selected_month = st.selectbox(
        "Month Filter",
        month_options,
        index=month_options.index(default_month),
        format_func=lambda value: pd.to_datetime(value + "-01").strftime("%B %Y"),
        key="breakdown_hours_month_filter",
    )

    selected_rows = bm[bm["month_key"] == selected_month]
    selected_hours = float(selected_rows["breakdown_hours"].sum())
    selected_jobs = int(selected_rows["job_id"].nunique())
    selected_label = pd.to_datetime(selected_month + "-01").strftime("%B %Y")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Current Month Hours\n{current_label}", f"{current_hours:.2f} hr")
    m2.metric("Current Month Jobs", current_jobs)
    m3.metric(f"Selected Month Hours\n{selected_label}", f"{selected_hours:.2f} hr")
    m4.metric("Total Breakdown Jobs", selected_jobs)

    st.markdown("#### 📈 Month-wise Breakdown Hours Trend")
    trend = monthly[["month_label", "breakdown_hours"]].set_index("month_label")
    st.line_chart(trend, y="breakdown_hours", use_container_width=True)
    st.caption(
        "Month Start Date/Time ke basis par assign hota hai; hours Start Time aur End Time ke difference se calculate hote hain."
    )
    st.markdown("---")


class _TabProxy:
    def __init__(self, base, inject_summary=False):
        self._base = base
        self._inject_summary = inject_summary

    def __enter__(self):
        entered = self._base.__enter__()
        if self._inject_summary:
            caller = inspect.currentframe().f_back
            _render_breakdown_hours_summary(caller.f_globals)
        return entered

    def __exit__(self, exc_type, exc, tb):
        return self._base.__exit__(exc_type, exc, tb)


def _tabs_with_breakdown_summary(labels, *args, **kwargs):
    bases = _ORIGINAL_TABS(labels, *args, **kwargs)
    is_main_navigation = "📋 Breakdown History" in labels
    if not is_main_navigation:
        return bases
    return [
        _TabProxy(base, inject_summary=(label == "📋 Breakdown History"))
        for base, label in zip(bases, labels)
    ]


st.tabs = _tabs_with_breakdown_summary
importlib.import_module("legacy_app")
