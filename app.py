"""AQPL Maintenance Dashboard entrypoint.

Stability-first entrypoint: load the proven dashboard directly from legacy_app.
The previous st.tabs monkeypatch used for Breakdown Hours Summary could leave
mobile Streamlit sessions on a blank shell during startup/reconnect.
"""

from legacy_app import *  # noqa: F401,F403
