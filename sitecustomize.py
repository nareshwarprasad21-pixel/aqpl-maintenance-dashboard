"""Small startup patch for AQPL Streamlit runtime source fixes."""
from pathlib import Path

_original_read_text = Path.read_text


def _aqpl_read_text(self, *args, **kwargs):
    text = _original_read_text(self, *args, **kwargs)
    if self.name == "legacy_app.py":
        old = """    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
        new = """    if machine_code=='aqpl/ter lax cls scr':\n        return 'Classification screen'\n    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
        if old in text:
            text = text.replace(old, new, 1)
    return text


Path.read_text = _aqpl_read_text
