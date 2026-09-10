"""AQPL Maintenance Dashboard entrypoint.

Stability-first entrypoint: load the proven dashboard directly from legacy_app,
then add a lightweight Breakdown Hours Summary in the sidebar.  This avoids
patching Streamlit internals (especially ``st.tabs``), which can make mobile
sessions unreliable during startup/reconnect.
"""

from legacy_app import *  # noqa: F401,F403


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
