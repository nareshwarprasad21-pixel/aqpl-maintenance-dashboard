"""AQPL Maintenance Dashboard entrypoint.

Run the proven dashboard script on every Streamlit rerun.  Importing
``legacy_app`` normally is intentionally avoided because Python caches imported
modules; after the first render, a Streamlit reconnect/rerun could otherwise
produce a blank page until the app process was rebooted.

This entrypoint also applies small, isolated UI enhancements at runtime:
- PM Action and Remark fields become searchable suggestion boxes.
- Daily Work Log mapped-machine selection starts blank so the user must choose.
"""

from pathlib import Path


DASHBOARD_SCRIPT = Path(__file__).with_name("legacy_app.py")
source = DASHBOARD_SCRIPT.read_text(encoding="utf-8")

old_block = """        results=[]
        with st.form(f'pmform_{pm_key}'):
            h1,h2,h3,h4,h5=st.columns([0.7,4.6,2,3.4,3.4])
            h1.markdown('**S.No.**'); h2.markdown('**Check Points**'); h3.markdown('**Status**'); h4.markdown('**Actions**'); h5.markdown('**Remarks**')
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c,d,e=st.columns([0.7,4.6,2,3.4,3.4])
                a.write(i)
                b.write(pt)
                status=c.selectbox('Status',['OK','NOT OK','N/A'],key=f'{pm_key}_s{i}',label_visibility='collapsed')
                action_txt=d.text_input('Action',key=f'{pm_key}_a{i}',label_visibility='collapsed',placeholder='Work/action done')
                remark=e.text_input('Remark',key=f'{pm_key}_r{i}',label_visibility='collapsed',placeholder='Observation/condition')
                results.append((pt,status,action_txt,remark))
"""

new_block = """        # Load the saved wording once for the selected machine so the PM form
        # remains fast even when a checklist has many points.
        pm_suggestion_history=q(
            'select check_point,action,remark from pm_checks where machine_code=? order by id desc',
            (code,)
        )

        def pm_saved_suggestions(check_point, field_name, limit=8):
            \"\"\"Return recent unique sentences saved for this exact PM point.\"\"\"
            if pm_suggestion_history.empty or field_name not in pm_suggestion_history.columns:
                return []
            point_key=str(check_point).strip().casefold()
            rows=pm_suggestion_history[
                pm_suggestion_history['check_point'].fillna('').astype(str).str.strip().str.casefold()==point_key
            ]
            suggestions=[]
            seen=set()
            for value in rows[field_name].tolist():
                text='' if value is None else str(value).strip()
                if not text or text.casefold() in ('nan','none'):
                    continue
                normalized=text.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                suggestions.append(text)
                if len(suggestions)>=limit:
                    break
            return suggestions

        results=[]
        with st.form(f'pmform_{pm_key}'):
            h1,h2,h3,h4,h5=st.columns([0.7,4.6,2,3.4,3.4])
            h1.markdown('**S.No.**'); h2.markdown('**Check Points**'); h3.markdown('**Status**'); h4.markdown('**Actions**'); h5.markdown('**Remarks**')
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c,d,e=st.columns([0.7,4.6,2,3.4,3.4])
                a.write(i)
                b.write(pt)
                status=c.selectbox('Status',['OK','NOT OK','N/A'],key=f'{pm_key}_s{i}',label_visibility='collapsed')
                action_options=pm_saved_suggestions(pt,'action')
                remark_options=pm_saved_suggestions(pt,'remark')
                action_txt=d.selectbox(
                    'Action',action_options,index=None,key=f'{pm_key}_a{i}',
                    label_visibility='collapsed',
                    placeholder='Previous action / type new',
                    accept_new_options=True
                ) or ''
                remark=e.selectbox(
                    'Remark',remark_options,index=None,key=f'{pm_key}_r{i}',
                    label_visibility='collapsed',
                    placeholder='Previous observation / type new',
                    accept_new_options=True
                ) or ''
                results.append((pt,status,action_txt,remark))
"""

if old_block in source:
    source = source.replace(old_block, new_block, 1)

# Daily Work Log: do not preselect the first mapped machine.  Keeping index=None
# makes the field visibly empty until the user deliberately chooses a machine.
daily_machine_old = """            daily_machine_options=MACH.machine_code.tolist()
            daily_code=st.selectbox(
                'Machine',
                daily_machine_options,
                format_func=lambda value:f\"{machine_row(value).machine_name} | {value}\"
            )
            misc_machine_name=''; misc_machine_code=''; misc_location=''
"""

daily_machine_new = """            daily_machine_options=MACH.machine_code.tolist()
            daily_code=st.selectbox(
                'Machine',
                daily_machine_options,
                index=None,
                placeholder='Select Machine',
                format_func=lambda value:f\"{machine_row(value).machine_name} | {value}\"
            )
            misc_machine_name=''; misc_machine_code=''; misc_location=''
"""

if daily_machine_old in source:
    source = source.replace(daily_machine_old, daily_machine_new, 1)

# Prevent Save from reaching machine_row(None) when the mapped-machine field is
# still blank.  Show a clear validation message instead.
daily_validation_old = """        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""

daily_validation_new = """        elif daily_code is None:st.error('Please select a Machine before saving the Daily Work Entry.')
        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""

if daily_validation_old in source:
    source = source.replace(daily_validation_old, daily_validation_new, 1)

# Execute with the real legacy file path so its existing __file__ based paths
# (database, data files, logo assets, etc.) keep working exactly as before.
runtime_globals = {
    "__name__": "__main__",
    "__file__": str(DASHBOARD_SCRIPT),
    "__package__": None,
    "__cached__": None,
}
exec(compile(source, str(DASHBOARD_SCRIPT), "exec"), runtime_globals)
