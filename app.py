"""AQPL Maintenance Dashboard entrypoint.

Stability-first entrypoint.  Keep startup as simple as possible so mobile
Streamlit/WebView sessions do not get stuck on a blank shell during reconnect.
All dashboard UI is rendered directly by legacy_app.py.
"""

from legacy_app import *  # noqa: F401,F403
