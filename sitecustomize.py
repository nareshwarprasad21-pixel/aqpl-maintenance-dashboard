"""Small startup patch for AQPL Streamlit runtime source fixes."""
from pathlib import Path

_original_read_text = Path.read_text


def _aqpl_read_text(self, *args, **kwargs):
    text = _original_read_text(self, *args, **kwargs)
    if self.name == "legacy_app.py":
        # Existing Classification screen machine-type fix.
        old = """    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
        new = """    if machine_code=='aqpl/ter lax cls scr':\n        return 'Classification screen'\n    if 'b.c.' in machine_name:\n        return 'BELT CONVEYOR'\n    return str(_value_or(machine.location,''))"""
        if old in text:
            text = text.replace(old, new, 1)

        # PM page: add ALL MACHINES to the real Machine Code selector.
        pm_old = """with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
    mr=machine_row(code)
    sheet=checklist_for(code)
"""
        pm_new = """with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',['ALL MACHINES']+MACH.machine_code.tolist(),key='pmcode')
    if code=='ALL MACHINES':
        st.markdown('### 📚 All Machines PM Check Sheets - Download / Print')
        st.caption('Select a date range to view and download saved PM sheets for every machine. PM entry remains machine-specific.')
        af1,af2,af3=st.columns([1,1,1])
        all_from=af1.date_input('From Date',value=TODAY.replace(day=1),key='all_pm_from')
        all_to=af2.date_input('To Date',value=TODAY,key='all_pm_to')
        all_search=af3.button('🔎 Search All Machines',key='all_pm_search',use_container_width=True)
        if all_search:
            if all_from>all_to:
                st.error('From Date cannot be after To Date.')
            else:
                st.session_state['all_pm_range']=(all_from,all_to)
        range_from,range_to=st.session_state.get('all_pm_range',(all_from,all_to))
        all_jobs=q(\"select * from jobs where job_type='PM' order by opened_at desc,machine_code\")
        if not all_jobs.empty:
            all_jobs=all_jobs.copy()
            all_jobs['_maintenance_dt']=pd.to_datetime(all_jobs['opened_at'],errors='coerce')
            all_jobs=all_jobs[(all_jobs['_maintenance_dt'].dt.date>=range_from)&(all_jobs['_maintenance_dt'].dt.date<=range_to)]
        if all_jobs.empty:
            st.info(f'No saved PM Check Sheets found from {range_from.strftime(\"%d-%m-%Y\")} to {range_to.strftime(\"%d-%m-%Y\")}.')
        else:
            st.success(f'{len(all_jobs)} saved PM sheet(s) found across {all_jobs.machine_code.nunique()} machine(s).')
            import zipfile
            all_zip_buffer=BytesIO()
            with zipfile.ZipFile(all_zip_buffer,'w',zipfile.ZIP_DEFLATED) as all_pm_zip:
                for _,all_job in all_jobs.iterrows():
                    all_jid=str(all_job['job_id'])
                    all_code=str(all_job['machine_code'])
                    all_checks=q('select check_point,result,action,remark from pm_checks where job_id=? order by id',(all_jid,))
                    if all_checks.empty:
                        continue
                    try:
                        all_machine=machine_row(all_code)
                    except Exception:
                        continue
                    all_dt=pd.to_datetime(all_job.get('opened_at'),errors='coerce')
                    all_date=all_dt.strftime('%d-%m-%Y') if not pd.isna(all_dt) else str(all_job.get('opened_at',''))
                    all_pdf=build_pm_checksheet_pdf(all_job,all_checks,all_machine)
                    safe_code=re.sub(r'[^A-Za-z0-9_-]+','-',all_code)
                    safe_jid=all_jid.replace('/','-')
                    pdf_name=f'PM_Check_Sheet_{safe_jid}_{all_date.replace(\"-\",\"\")}.pdf'
                    all_pm_zip.writestr(f'{safe_code}/{pdf_name}',all_pdf)
                    c1,c2,c3,c4=st.columns([1.5,1.3,2.2,1.3])
                    c1.write(all_code); c2.write(all_date); c3.code(all_jid)
                    c4.download_button('⬇️ PDF',data=all_pdf,file_name=pdf_name,mime='application/pdf',key=f'all_pm_pdf_{safe_jid}',on_click='ignore',use_container_width=True)
            all_zip_buffer.seek(0)
            st.download_button('📦 Download All Machines PM Sheets',data=all_zip_buffer.getvalue(),file_name=f'AQPL_All_Machines_PM_{range_from.strftime(\"%Y%m%d\")}_{range_to.strftime(\"%Y%m%d\")}.zip',mime='application/zip',key=f'all_pm_zip_{range_from}_{range_to}',on_click='ignore',use_container_width=True)
        st.stop()
    mr=machine_row(code)
    sheet=checklist_for(code)
"""
        if pm_old in text:
            text = text.replace(pm_old, pm_new, 1)
    return text


Path.read_text = _aqpl_read_text
