"""AQPL startup source patch.
Patches the exact legacy PM selector used by the deployed Streamlit app.
"""
from pathlib import Path

_original_read_text = Path.read_text


def _aqpl_read_text(self, *args, **kwargs):
    text = _original_read_text(self, *args, **kwargs)
    if self.name != "legacy_app.py":
        return text

    # Existing classification-screen compatibility patch.
    old_cls = """    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
    new_cls = """    if machine_code=='aqpl/ter lax cls scr':\n        return 'Classification screen'\n    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
    if old_cls in text:
        text = text.replace(old_cls, new_cls, 1)

    # Dedicated TOMRA Screen-1 PM checklist requested for AQPL/TOM SCR-1.
    tom_anchor = "STATIC_MACH,PLAN,CHECKS=load_static('2026-09-06-pm-plan-2026-27-v2')"
    tom_repl = tom_anchor + "\nCHECKS['TOMRA SCREEN-1']=['Check vibration motor cable','Check wire mesh','Check body nuts and bolts','Check vibration spring','Check extra noise and vibration','Check inlet and discharge chute']"
    if tom_anchor in text:
        text = text.replace(tom_anchor, tom_repl, 1)

    tom_map_old = """def checklist_for(code):\n    # Dedicated pneumatic-line checklist must override any stale mapping row."""
    tom_map_new = """def checklist_for(code):\n    # Dedicated TOMRA Screen-1 checklist must override any stale mapping row.\n    if code=='AQPL/TOM SCR-1':return 'TOMRA SCREEN-1'\n    # Dedicated pneumatic-line checklist must override any stale mapping row."""
    if tom_map_old in text:
        text = text.replace(tom_map_old, tom_map_new, 1)

    # IMPORTANT: actual legacy source has st.subheader and selectbox on separate lines.
    # Patch only the selectbox + following machine_row line so whitespace around the tab block cannot break matching.
    old_pm = """    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')\n    mr=machine_row(code)"""
    new_pm = """    code=st.selectbox('Machine Code',['ALL MACHINES']+MACH.machine_code.tolist(),key='pmcode')\n    if code=='ALL MACHINES':\n        st.markdown('### 📚 All Machines PM Check Sheets - Download / Print')\n        st.caption('Choose From Date and To Date to retrieve saved PM sheets for every machine.')\n        _af1,_af2,_af3=st.columns([1,1,1])\n        _all_from=_af1.date_input('From Date',value=TODAY.replace(day=1),key='all_pm_from')\n        _all_to=_af2.date_input('To Date',value=TODAY,key='all_pm_to')\n        _all_search=_af3.button('🔎 Search History',key='all_pm_search',use_container_width=True)\n        if _all_search and _all_from<=_all_to:\n            st.session_state['all_pm_range']=(_all_from,_all_to)\n        if _all_from>_all_to:\n            st.error('From Date cannot be after To Date.')\n        _range_from,_range_to=st.session_state.get('all_pm_range',(_all_from,_all_to))\n        _all_jobs=q(\"select * from jobs where job_type='PM' order by opened_at desc\")\n        if not _all_jobs.empty:\n            _all_jobs=_all_jobs.copy()\n            _all_jobs['_pm_dt']=pd.to_datetime(_all_jobs['opened_at'],errors='coerce')\n            _all_jobs=_all_jobs[(_all_jobs['_pm_dt'].dt.date>=_range_from)&(_all_jobs['_pm_dt'].dt.date<=_range_to)]\n        if _all_jobs.empty:\n            st.info(f'No saved PM Check Sheets found from {_range_from:%d-%m-%Y} to {_range_to:%d-%m-%Y}.')\n        else:\n            import zipfile\n            _zip_buffer=BytesIO()\n            _pdf_count=0\n            with zipfile.ZipFile(_zip_buffer,'w',zipfile.ZIP_DEFLATED) as _pm_zip:\n                for _,_job in _all_jobs.iterrows():\n                    _jid=str(_job['job_id']); _mcode=str(_job['machine_code'])\n                    _checks=q('select check_point,result,action,remark from pm_checks where job_id=? order by id',(_jid,))\n                    if _checks.empty:\n                        continue\n                    try:\n                        _machine=machine_row(_mcode)\n                        _pdf=build_pm_checksheet_pdf(_job,_checks,_machine)\n                    except Exception:\n                        continue\n                    _dt=pd.to_datetime(_job.get('opened_at'),errors='coerce')\n                    _date=_dt.strftime('%d-%m-%Y') if not pd.isna(_dt) else ''\n                    _safe_code=re.sub(r'[^A-Za-z0-9_-]+','-',_mcode)\n                    _safe_jid=_jid.replace('/','-')\n                    _name=f'{_safe_code}/PM_Check_Sheet_{_safe_jid}_{_date.replace(\"-\",\"\")}.pdf'\n                    _pm_zip.writestr(_name,_pdf); _pdf_count+=1\n                    _c1,_c2,_c3,_c4=st.columns([1.5,1.2,2.2,1.2])\n                    _c1.write(_mcode); _c2.write(_date); _c3.code(_jid)\n                    _c4.download_button('⬇️ PDF',data=_pdf,file_name=_name.split('/')[-1],mime='application/pdf',key=f'allpm_{_safe_jid}',on_click='ignore',use_container_width=True)\n            _zip_buffer.seek(0)\n            st.success(f'{_pdf_count} saved PM sheet(s) ready for download.')\n            st.download_button('📦 Download All in Date Range',data=_zip_buffer.getvalue(),file_name=f'AQPL_All_Machines_PM_{_range_from:%Y%m%d}_{_range_to:%Y%m%d}.zip',mime='application/zip',key=f'all_pm_zip_{_range_from}_{_range_to}',on_click='ignore',use_container_width=True)\n        st.stop()\n    mr=machine_row(code)"""
    if old_pm in text:
        text = text.replace(old_pm, new_pm, 1)
    return text


Path.read_text = _aqpl_read_text
