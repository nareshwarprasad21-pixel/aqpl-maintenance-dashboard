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

        # PM Check Sheet selector: expose ALL MACHINES in the actual multiline legacy block.
        old_pm = """with T[2]:\n    st.subheader('Preventive Maintenance Check Sheet')\n    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')"""
        new_pm = """with T[2]:\n    st.subheader('Preventive Maintenance Check Sheet')\n    code=st.selectbox('Machine Code',['ALL MACHINES']+MACH.machine_code.tolist(),key='pmcode')\n    if code=='ALL MACHINES':\n        st.info('ALL MACHINES selected. Use the All Machines PM History / Download section below for date-wise saved PM sheets.')\n        st.stop()"""
        if old_pm in text:
            text = text.replace(old_pm, new_pm, 1)
    return text


Path.read_text = _aqpl_read_text
