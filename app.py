"""AQPL Maintenance Dashboard entrypoint.

Run the proven dashboard script on every Streamlit rerun.  Importing
``legacy_app`` normally is intentionally avoided because Python caches imported
modules; after the first render, a Streamlit reconnect/rerun could otherwise
produce a blank page until the app process was rebooted.
"""

from pathlib import Path
import runpy


DASHBOARD_SCRIPT = Path(__file__).with_name("legacy_app.py")
runpy.run_path(str(DASHBOARD_SCRIPT), run_name="__main__")
