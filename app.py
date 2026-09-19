"""AQPL Maintenance Dashboard entrypoint with runtime enhancements."""
from pathlib import Path
import re as _runtime_re

DASHBOARD_SCRIPT = Path(__file__).with_name("legacy_app.py")
source = DASHBOARD_SCRIPT.read_text(encoding="utf-8")

# Breakdown Maintenance: date-range/month-wise report + CSV download.
_bm_report_anchor="""            st.success(f'{jid} saved → Breakdown {start_iso} से {end_iso} तक चला। Total time: {duration_hours} hour(s) {duration_minutes} minute(s). Machine History + Breakdown History + Why-Why draft + applicable Permit draft(s) linked automatically.')

with T[4]:"""
_bm_report_repl="""            st.success(f'{jid} saved → Breakdown {start_iso} से {end_iso} तक चला। Total time: {duration_hours} hour(s) {duration_minutes} minute(s). Machine History + Breakdown History + Why-Why draft + applicable Permit draft(s) linked automatically.')

    st.markdown('### 📥 Breakdown Maintenance Report - Date Range / Month-wise')
    st.caption('From Date और To Date चुनकर selected period या पूरे month की Breakdown Maintenance report निकालें।')
    br1,br2=st.columns(2)
    bm_report_from=br1.date_input('From Date',value=TODAY.replace(day=1),key='bm_report_from')
    bm_report_to=br2.date_input('To Date',value=TODAY,key='bm_report_to')
    if bm_report_from>bm_report_to:
        st.error('From Date cannot be after To Date.')
    else:
        bm_report=q(\"select id,machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark from breakdown_activity_log order by activity_dt desc\")
        if not bm_report.empty:
            bm_report=bm_report.copy(); bm_report['_dt']=pd.to_datetime(bm_report['activity_dt'],errors='coerce')
            bm_report=bm_report[(bm_report['_dt'].dt.date>=bm_report_from)&(bm_report['_dt'].dt.date<=bm_report_to)]
        if bm_report.empty:
            st.info(f'No Breakdown Maintenance record found from {bm_report_from.strftime(\"%d-%m-%Y\")} to {bm_report_to.strftime(\"%d-%m-%Y\")}.')
        else:
            bm_report['Date']=bm_report['_dt'].dt.strftime('%d-%m-%Y')
            bm_report['Start Time']=bm_report['_dt'].dt.strftime('%H:%M')
            report_cols=['Date','Start Time','job_id','machine_code','failure','cause','action','spares','downtime_hr','status','remark']
            bm_display=bm_report[report_cols].rename(columns={'job_id':'Job ID','machine_code':'Machine Code','failure':'Breakdown / Problem','cause':'Cause','action':'Action Taken','spares':'Spares / Material','downtime_hr':'Downtime (Hours)','status':'Status','remark':'Remarks'})
            st.success(f'{len(bm_display)} breakdown record(s) found. Total downtime: {pd.to_numeric(bm_display[\"Downtime (Hours)\"],errors=\"coerce\").fillna(0).sum():.2f} hours.')
            st.dataframe(bm_display,use_container_width=True,hide_index=True)
            st.download_button('⬇️ Download Breakdown Report CSV',data=bm_display.to_csv(index=False).encode('utf-8-sig'),file_name=f'AQPL_Breakdown_Report_{bm_report_from.strftime(\"%Y%m%d\")}_{bm_report_to.strftime(\"%Y%m%d\")}.csv',mime='text/csv',key='bm_report_csv',use_container_width=True)

with T[4]:"""
if _bm_report_anchor in source:
    source=source.replace(_bm_report_anchor,_bm_report_repl,1)

# Reusable Classification screen template.
_classification_anchor="STATIC_MACH,PLAN,CHECKS=load_static('2026-09-06-pm-plan-2026-27-v2')"
_classification_repl=_classification_anchor+"\n_base_classification=list(CHECKS.get('Tertiary class screen',CHECKS.get('Vibro screen',[])))\nCHECKS['Classification screen']=[pt for idx,pt in enumerate(_base_classification,1) if idx not in (6,7,8,10)]"
if _classification_anchor in source: source=source.replace(_classification_anchor,_classification_repl,1)

# PM Action / Remark smart + saved suggestions for all machines/checkpoints.
old_block="""        results=[]
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
new_block="""        pm_suggestion_history=q('select machine_code,check_point,action,remark from pm_checks order by id desc')
        def pm_smart_defaults(check_point,field_name):
            k=str(check_point).strip().casefold()
            if field_name=='action':
                if any(x in k for x in ['clean','filter','dust']): specific=['Checked and cleaned','Cleaning done']
                elif any(x in k for x in ['grease','lubric','oil']): specific=['Checked and lubricated','Lubrication done']
                elif any(x in k for x in ['tight','bolt','nut','fastener']): specific=['Checked and tightened','Tightening done']
                elif any(x in k for x in ['belt','chain','coupling','alignment','tension']): specific=['Checked and adjusted','Alignment/tension checked']
                elif any(x in k for x in ['leak','hose','pipe','valve','seal']): specific=['Checked for leakage','Checked and found no leakage']
                elif any(x in k for x in ['bearing','vibration','noise','temperature']): specific=['Checked during running','Condition checked']
                elif any(x in k for x in ['motor','electrical','cable','terminal','panel']): specific=['Checked electrical condition','Connections checked']
                else: specific=['Checked','Inspected']
                return specific+['Checked and found OK','Checked and found in good condition','No action required']
            if any(x in k for x in ['leak','hose','pipe','valve','seal']): specific=['No leakage observed','Condition found satisfactory']
            elif any(x in k for x in ['bearing','vibration','noise']): specific=['Running normal; no abnormal noise/vibration','Condition found normal']
            elif 'temperature' in k: specific=['Temperature found normal','No overheating observed']
            elif any(x in k for x in ['belt','chain','coupling','alignment','tension']): specific=['Alignment/tension found OK','Condition found satisfactory']
            elif any(x in k for x in ['motor','electrical','cable','terminal','panel']): specific=['Electrical condition found OK','No abnormality observed']
            elif any(x in k for x in ['clean','filter','dust']): specific=['Clean and in good condition','No abnormal accumulation observed']
            else: specific=['Found in good condition','Condition found satisfactory']
            return specific+['No abnormality observed','OK']
        def pm_saved_suggestions(check_point,field_name,limit=10):
            out=[]; seen=set(); key=str(check_point).strip().casefold()
            if not pm_suggestion_history.empty and field_name in pm_suggestion_history.columns:
                rows=pm_suggestion_history[pm_suggestion_history['check_point'].fillna('').astype(str).str.strip().str.casefold()==key]
                if 'machine_code' in rows.columns:
                    same=rows[rows['machine_code'].fillna('').astype(str)==str(code)]; other=rows[rows['machine_code'].fillna('').astype(str)!=str(code)]; rows=pd.concat([same,other],ignore_index=True)
                for value in rows[field_name].tolist():
                    text='' if value is None else str(value).strip(); norm=text.casefold()
                    if not text or norm in ('nan','none') or norm in seen: continue
                    seen.add(norm); out.append(text)
                    if len(out)>=limit: break
            for text in pm_smart_defaults(check_point,field_name):
                norm=text.casefold()
                if norm not in seen: seen.add(norm); out.append(text)
            return out
        results=[]
        with st.form(f'pmform_{pm_key}'):
            h1,h2,h3,h4,h5=st.columns([0.7,4.6,2,3.4,3.4]); h1.markdown('**S.No.**'); h2.markdown('**Check Points**'); h3.markdown('**Status**'); h4.markdown('**Actions**'); h5.markdown('**Remarks**')
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c,d,e=st.columns([0.7,4.6,2,3.4,3.4]); a.write(i); b.write(pt)
                status=c.selectbox('Status',['OK','NOT OK','N/A'],key=f'{pm_key}_s{i}',label_visibility='collapsed')
                action_txt=d.selectbox('Action',pm_saved_suggestions(pt,'action'),index=None,key=f'{pm_key}_a{i}',label_visibility='collapsed',placeholder='Suggested / previous action / type new',accept_new_options=True) or ''
                remark=e.selectbox('Remark',pm_saved_suggestions(pt,'remark'),index=None,key=f'{pm_key}_r{i}',label_visibility='collapsed',placeholder='Suggested / previous observation / type new',accept_new_options=True) or ''
                results.append((pt,status,action_txt,remark))
"""
if old_block in source: source=source.replace(old_block,new_block,1)

# Add linked permit details to every generated PM PDF, without changing PM saving logic.
pm_meta_anchor="""    meta_table=Table(meta,colWidths=[30*mm,61*mm,32*mm,61*mm])"""
pm_meta_repl="""    try:
        linked_permits=q('select permit_no,permit_type,status,supervisor,start_dt,end_dt,precautions from permits where job_id=? order by id',(val(job,'job_id'),))
        if not linked_permits.empty:
            permit_text=[]
            for _,p in linked_permits.iterrows():
                permit_text.append(f\"{p.get('permit_type','')} | Permit: {p.get('permit_no','')} | Status: {p.get('status','')} | Supervisor: {p.get('supervisor','') or '-'} | Start: {p.get('start_dt','') or '-'} | End: {p.get('end_dt','') or '-'} | Precautions: {p.get('precautions','') or '-'}\")
            meta.append([Paragraph('<b>Safety / Permit Details</b>',body_bold),Paragraph(escape(' ; '.join(permit_text)),body_style),Paragraph('',body_style),Paragraph('',body_style)])
    except Exception:
        pass
    meta_table=Table(meta,colWidths=[30*mm,61*mm,32*mm,61*mm])"""
if pm_meta_anchor in source: source=source.replace(pm_meta_anchor,pm_meta_repl,1)

# Replace saved PM selector with machine-wise From/To date history and individual/batch PDF downloads.
saved_pm_old="""        st.markdown('#### 📚 Saved PM Check Sheets - Download / Print')
        saved_pm_jobs=q(\"select * from jobs where machine_code=? and job_type='PM' order by opened_at desc\",(code,))
        if saved_pm_jobs.empty:
            st.info('इस machine की saved PM Check Sheet अभी उपलब्ध नहीं है।')
        else:
            saved_job_id=st.selectbox('Select saved PM Job / Work Order ID',saved_pm_jobs.job_id.tolist(),key=f'saved_pm_job_{code}')
            saved_job=saved_pm_jobs[saved_pm_jobs.job_id==saved_job_id].iloc[0]
            saved_checks=q('select check_point,result,action,remark from pm_checks where job_id=? order by id',(saved_job_id,))
            if saved_checks.empty:
                st.warning('इस Job ID के checklist details उपलब्ध नहीं हैं।')
            else:
                saved_pdf=build_pm_checksheet_pdf(saved_job,saved_checks,mr)
                st.download_button('⬇️ Download Saved PM Check Sheet PDF',data=saved_pdf,
                    file_name=f\"PM_Check_Sheet_{saved_job_id.replace('/','-')}.pdf\",mime='application/pdf',
                    key=f'saved_pm_pdf_{saved_job_id}',on_click='ignore')
"""
saved_pm_new="""        st.markdown('#### 📚 Saved PM Check Sheets - Download / Print')
        st.caption(f'History is filtered only for selected Machine Code: {code}')
        hf1,hf2,hf3=st.columns([1,1,1])
        history_from=hf1.date_input('From Date',value=TODAY.replace(day=1),key=f'pm_history_from_{pm_key}')
        history_to=hf2.date_input('To Date',value=TODAY,key=f'pm_history_to_{pm_key}')
        search_history=hf3.button('🔎 Search History',key=f'pm_history_search_{pm_key}',use_container_width=True)
        state_key=f'pm_history_range_{pm_key}'
        if search_history:
            if history_from>history_to:
                st.error('From Date cannot be after To Date.')
            else:
                st.session_state[state_key]=(history_from,history_to)
        active_from,active_to=st.session_state.get(state_key,(history_from,history_to))
        saved_pm_jobs=q(\"select * from jobs where machine_code=? and job_type='PM' order by opened_at desc\",(code,))
        if not saved_pm_jobs.empty:
            saved_pm_jobs=saved_pm_jobs.copy()
            saved_pm_jobs['_maintenance_dt']=pd.to_datetime(saved_pm_jobs['opened_at'],errors='coerce')
            saved_pm_jobs=saved_pm_jobs[(saved_pm_jobs['_maintenance_dt'].dt.date>=active_from)&(saved_pm_jobs['_maintenance_dt'].dt.date<=active_to)]
        if saved_pm_jobs.empty:
            st.info(f'No saved PM Check Sheet found for {code} from {active_from.strftime(\"%d-%m-%Y\")} to {active_to.strftime(\"%d-%m-%Y\")}.')
        else:
            st.success(f'{len(saved_pm_jobs)} PM record(s) found for {code}.')
            import zipfile
            batch_buffer=BytesIO()
            with zipfile.ZipFile(batch_buffer,'w',zipfile.ZIP_DEFLATED) as pm_zip:
                for _,saved_job in saved_pm_jobs.iterrows():
                    saved_job_id=str(saved_job['job_id'])
                    saved_checks=q('select check_point,result,action,remark from pm_checks where job_id=? order by id',(saved_job_id,))
                    maintenance_dt=pd.to_datetime(saved_job.get('opened_at'),errors='coerce')
                    maintenance_label=maintenance_dt.strftime('%d-%m-%Y') if not pd.isna(maintenance_dt) else str(saved_job.get('opened_at',''))
                    r1,r2,r3=st.columns([1.2,2.2,1.5])
                    r1.markdown(f'**{maintenance_label}**')
                    r2.markdown(f'`{saved_job_id}`')
                    if saved_checks.empty:
                        r3.caption('Checklist details unavailable')
                        continue
                    saved_pdf=build_pm_checksheet_pdf(saved_job,saved_checks,mr)
                    safe_job=saved_job_id.replace('/','-')
                    pdf_name=f'PM_Check_Sheet_{safe_job}_{maintenance_label.replace(\"-\",\"\")}.pdf'
                    r3.download_button('⬇️ Download PDF',data=saved_pdf,file_name=pdf_name,mime='application/pdf',key=f'pm_hist_pdf_{pm_key}_{safe_job}',on_click='ignore',use_container_width=True)
                    pm_zip.writestr(pdf_name,saved_pdf)
            batch_buffer.seek(0)
            st.download_button('📦 Download All in Date Range',data=batch_buffer.getvalue(),file_name=f'PM_History_{pm_key}_{active_from.strftime(\"%Y%m%d\")}_{active_to.strftime(\"%Y%m%d\")}.zip',mime='application/zip',key=f'pm_hist_all_{pm_key}_{active_from}_{active_to}',on_click='ignore',use_container_width=True)
"""
if saved_pm_old in source: source=source.replace(saved_pm_old,saved_pm_new,1)

# ALL MACHINES PM history/download. Keep q() SQL inside its supported parser grammar: one ORDER BY column only.
_pm_all_handler="""    st.subheader('Preventive Maintenance Check Sheet')
    show_all_pm=st.checkbox('📚 Search completed PM sheets across all machines',key='show_all_pm_history')
    if show_all_pm:
        st.markdown('### 📚 All Machines PM Check Sheets - Download / Print')
        st.caption('Select a date range to collect saved PM documents for every machine. Each PDF is the original completed PM check sheet, not a generic table.')
        af1,af2,af3=st.columns([1,1,1])
        all_from=af1.date_input('From Date',value=TODAY.replace(day=1),key='all_pm_from')
        all_to=af2.date_input('To Date',value=TODAY,key='all_pm_to')
        all_search=af3.button('🔎 Search All Machines',key='all_pm_search',use_container_width=True)
        if all_search:
            if all_from>all_to: st.error('From Date cannot be after To Date.')
            else: st.session_state['all_pm_range']=(all_from,all_to)
        range_from,range_to=st.session_state.get('all_pm_range',(all_from,all_to))
        all_jobs=q(\"select * from jobs where job_type='PM' order by opened_at desc\")
        if not all_jobs.empty:
            all_jobs=all_jobs.copy(); all_jobs['_maintenance_dt']=pd.to_datetime(all_jobs['opened_at'],errors='coerce')
            all_jobs=all_jobs[(all_jobs['_maintenance_dt'].dt.date>=range_from)&(all_jobs['_maintenance_dt'].dt.date<=range_to)]
            all_jobs=all_jobs.sort_values(['_maintenance_dt','machine_code'],ascending=[False,True])
        if all_jobs.empty:
            st.info(f'No saved PM Check Sheets found from {range_from.strftime(\"%d-%m-%Y\")} to {range_to.strftime(\"%d-%m-%Y\")}.')
        else:
            st.success(f'{len(all_jobs)} saved PM sheet(s) found across {all_jobs.machine_code.nunique()} machine(s).')
            import zipfile
            all_zip_buffer=BytesIO()
            with zipfile.ZipFile(all_zip_buffer,'w',zipfile.ZIP_DEFLATED) as all_pm_zip:
                for _,all_job in all_jobs.iterrows():
                    all_jid=str(all_job['job_id']); all_code=str(all_job['machine_code'])
                    all_checks=q('select check_point,result,action,remark from pm_checks where job_id=? order by id',(all_jid,))
                    if all_checks.empty: continue
                    try: all_machine=machine_row(all_code)
                    except Exception: continue
                    all_dt=pd.to_datetime(all_job.get('opened_at'),errors='coerce'); all_date=all_dt.strftime('%d-%m-%Y') if not pd.isna(all_dt) else str(all_job.get('opened_at',''))
                    all_pdf=build_pm_checksheet_pdf(all_job,all_checks,all_machine)
                    safe_code=re.sub(r'[^A-Za-z0-9_-]+','-',all_code); safe_jid=all_jid.replace('/','-')
                    all_pdf_name=f'{safe_code}/PM_Check_Sheet_{safe_jid}_{all_date.replace(\"-\",\"\")}.pdf'
                    all_pm_zip.writestr(all_pdf_name,all_pdf)
                    c1,c2,c3,c4=st.columns([1.5,1.3,2.2,1.3]); c1.write(all_code); c2.write(all_date); c3.code(all_jid)
                    c4.download_button('⬇️ PDF',data=all_pdf,file_name=all_pdf_name.split('/')[-1],mime='application/pdf',key=f'all_pm_pdf_{safe_jid}',on_click='ignore',use_container_width=True)
            all_zip_buffer.seek(0)
            st.download_button('📦 Download All Machines PM Sheets',data=all_zip_buffer.getvalue(),file_name=f'AQPL_All_Machines_PM_{range_from.strftime(\"%Y%m%d\")}_{range_to.strftime(\"%Y%m%d\")}.zip',mime='application/zip',key=f'all_pm_zip_{range_from}_{range_to}',on_click='ignore',use_container_width=True)
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
    mr=machine_row(code)
    sheet=checklist_for(code)"""
_pm_pattern=r"(?m)^    st\.subheader\('Preventive Maintenance Check Sheet'\)\s*\n    code=st\.selectbox\('Machine Code',\['ALL MACHINES'\]\+MACH\.machine_code\.tolist\(\),key='pmcode'\)\s*\n    mr=machine_row\(code\)\s*\n    sheet=checklist_for\(code\)"
source,_pm_all_count=_runtime_re.subn(_pm_pattern,_pm_all_handler,source,count=1)
if _pm_all_count!=1:
    raise RuntimeError('AQPL ALL MACHINES PM handler could not be injected into legacy_app.py')

# Permit Additional Precautions autosuggestions, permit-type aware + previously saved entries.
permit_old="""        with st.form('permitform'):
            sup=st.text_input('Supervisor',value=str(r.supervisor or '')); activity=st.text_input('Activity',value=str(r.activity or '')); start=st.text_input('Start date/time',value=str(r.start_dt or '')); end=st.text_input('End date/time',value=str(r.end_dt or '')); precautions=st.text_area('Additional precautions / concern noticed',value=str(r.precautions or '')); status=st.selectbox('Permit Status',['DRAFT','GRANTED','CLOSED'],index=['DRAFT','GRANTED','CLOSED'].index(r.status if r.status in ['DRAFT','GRANTED','CLOSED'] else 'DRAFT')); save=st.form_submit_button('Save Permit')
        if save:execsql('update permits set supervisor=?,activity=?,start_dt=?,end_dt=?,precautions=?,status=? where permit_no=?',(sup,activity,start,end,precautions,status,pid));st.success('Permit updated.')
"""
permit_new="""        permit_type=str(r.permit_type or '').strip().upper()
        height_precautions=['No additional concern noticed','Full body harness and lifeline required','Work area barricaded; no person allowed below','Tools to be secured to prevent falling','Proper scaffolding / working platform required','LOTO to be ensured before starting work','Safe access ladder and working platform to be ensured','Safety helmet with chin strap and required PPE to be used']
        hot_precautions=['No additional concern noticed','Fire extinguisher kept ready; combustible material removed','Gas hoses, regulator and flashback arrestor checked','Fire watch to be maintained during hot work','LOTO to be ensured before starting work','Welding machine, holder and earthing connection checked','Hot work area barricaded and nearby material protected from sparks','Required PPE including welding shield, gloves and safety shoes to be used']
        default_precautions=height_precautions if 'HEIGHT' in permit_type else hot_precautions if 'HOT' in permit_type else ['No additional concern noticed','LOTO to be ensured before starting work','Work area barricaded and required PPE to be used']
        saved_precautions=q('select precautions from permits where permit_type=? order by id desc',(r.permit_type,))
        permit_options=[]; permit_seen=set()
        for value in saved_precautions['precautions'].tolist() if len(saved_precautions) and 'precautions' in saved_precautions.columns else []:
            text='' if value is None else str(value).strip(); norm=text.casefold()
            if text and norm not in ('none','nan') and norm not in permit_seen: permit_seen.add(norm); permit_options.append(text)
        for text in default_precautions:
            norm=text.casefold()
            if norm not in permit_seen: permit_seen.add(norm); permit_options.append(text)
        current_precaution=str(r.precautions or '').strip()
        if current_precaution and current_precaution.casefold() not in ('none','nan') and current_precaution.casefold() not in permit_seen: permit_options.insert(0,current_precaution)
        with st.form('permitform'):
            sup=st.text_input('Supervisor',value=str(r.supervisor or '')); activity=st.text_input('Activity',value=str(r.activity or '')); start=st.text_input('Start date/time',value=str(r.start_dt or '')); end=st.text_input('End date/time',value=str(r.end_dt or ''))
            precautions=st.selectbox('Additional precautions / concern noticed',permit_options,index=permit_options.index(current_precaution) if current_precaution in permit_options else None,placeholder='Select previous/suggested precaution or type new',accept_new_options=True)
            status=st.selectbox('Permit Status',['DRAFT','GRANTED','CLOSED'],index=['DRAFT','GRANTED','CLOSED'].index(r.status if r.status in ['DRAFT','GRANTED','CLOSED'] else 'DRAFT')); save=st.form_submit_button('Save Permit')
        if save:execsql('update permits set supervisor=?,activity=?,start_dt=?,end_dt=?,precautions=?,status=? where permit_no=?',(sup,activity,start,end,str(precautions or '').strip(),status,pid));st.success('Permit updated.')
"""
if permit_old in source: source=source.replace(permit_old,permit_new,1)

# Historical record workspace: make date-wise search and downloads consistent
# across the existing PM, Breakdown, Daily Work and Machine History tabs.
# PM is intentionally handled above with the original completed check-sheet PDF
# per result; the blocks below cover the other record types.
_bm_history_pattern=r"(?s)    st\.markdown\('### 📥 Breakdown Maintenance Report - Date Range / Month-wise'\).*?\n\nwith T\[4\]:"
_bm_history_repl="""    st.markdown('### 📥 Breakdown Maintenance History — Search & Download')
    st.caption('Machine Code और From/To Date चुनकर saved breakdown records देखें. हर result का printable Breakdown Report PDF या selected range का CSV / ZIP download करें।')
    br1,br2,br3=st.columns([1,1,1.35])
    bm_report_from=br1.date_input('From Date',value=TODAY.replace(day=1),key='bm_report_from')
    bm_report_to=br2.date_input('To Date',value=TODAY,key='bm_report_to')
    bm_source=q(\"select id,machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark from breakdown_activity_log order by activity_dt desc\")
    bm_machine_options=['ALL']+sorted([str(value) for value in bm_source['machine_code'].dropna().unique().tolist()]) if not bm_source.empty else ['ALL']
    bm_report_machine=br3.selectbox('Machine Filter',bm_machine_options,key='bm_report_machine')
    if bm_report_from>bm_report_to:
        st.error('From Date cannot be after To Date.')
    else:
        bm_filtered=bm_source.copy()
        if not bm_filtered.empty:
            bm_filtered['_dt']=pd.to_datetime(bm_filtered['activity_dt'],errors='coerce')
            bm_filtered=bm_filtered[(bm_filtered['_dt'].dt.date>=bm_report_from)&(bm_filtered['_dt'].dt.date<=bm_report_to)]
            if bm_report_machine!='ALL':
                bm_filtered=bm_filtered[bm_filtered['machine_code'].astype(str)==bm_report_machine]
        if bm_filtered.empty:
            st.info(f'No Breakdown Maintenance record found for selected filter from {bm_report_from.strftime(\"%d-%m-%Y\")} to {bm_report_to.strftime(\"%d-%m-%Y\")}.')
        else:
            bm_filtered=bm_filtered.copy()
            bm_filtered['Date']=bm_filtered['_dt'].dt.strftime('%d-%m-%Y')
            bm_filtered['Start Time']=bm_filtered['_dt'].dt.strftime('%H:%M')
            report_cols=['Date','Start Time','job_id','machine_code','failure','cause','action','spares','downtime_hr','status','remark']
            bm_display=bm_filtered[report_cols].rename(columns={'job_id':'Job ID','machine_code':'Machine Code','failure':'Breakdown / Problem','cause':'Cause','action':'Action Taken','spares':'Spares / Material','downtime_hr':'Downtime (Hours)','status':'Status','remark':'Remarks'})
            total_downtime=pd.to_numeric(bm_display['Downtime (Hours)'],errors='coerce').fillna(0).sum()
            st.success(f'{len(bm_display)} breakdown record(s) found. Total downtime: {total_downtime:.2f} hours.')
            st.dataframe(bm_display,use_container_width=True,hide_index=True)
            dl1,dl2=st.columns(2)
            dl1.download_button('⬇️ Download Filtered Breakdown CSV',data=bm_display.to_csv(index=False).encode('utf-8-sig'),file_name=f'AQPL_Breakdown_History_{bm_report_from.strftime(\"%Y%m%d\")}_{bm_report_to.strftime(\"%Y%m%d\")}.csv',mime='text/csv',key='bm_report_csv',use_container_width=True)
            import zipfile
            bm_jobs=q(\"select * from jobs where job_type='BM' order by opened_at desc\")
            bm_breakdowns=q(\"select * from breakdowns order by id desc\")
            bm_zip_buffer=BytesIO()
            with zipfile.ZipFile(bm_zip_buffer,'w',zipfile.ZIP_DEFLATED) as bm_zip:
                st.markdown('#### Individual Breakdown Reports')
                for row_number,(_,bm_row) in enumerate(bm_filtered.iterrows(),1):
                    bm_job_id=str(bm_row.get('job_id',''))
                    bm_code=str(bm_row.get('machine_code',''))
                    job_match=bm_jobs[bm_jobs['job_id'].astype(str)==bm_job_id] if not bm_jobs.empty else pd.DataFrame()
                    breakdown_match=bm_breakdowns[bm_breakdowns['job_id'].astype(str)==bm_job_id] if not bm_breakdowns.empty else pd.DataFrame()
                    report_job=job_match.iloc[0].to_dict() if len(job_match) else {'job_id':bm_job_id,'opened_at':str(bm_row.get('activity_dt','')),'closed_at':'','status':str(bm_row.get('status',''))}
                    report_breakdown=breakdown_match.iloc[0].to_dict() if len(breakdown_match) else bm_row.to_dict()
                    report_breakdown.update({'job_id':bm_job_id,'machine_code':bm_code,'failure':report_breakdown.get('failure',bm_row.get('failure','')),'cause':report_breakdown.get('cause',bm_row.get('cause','')),'action':report_breakdown.get('action',bm_row.get('action','')),'spares':report_breakdown.get('spares',bm_row.get('spares','')),'downtime_hr':report_breakdown.get('downtime_hr',bm_row.get('downtime_hr',0)),'status':report_breakdown.get('status',bm_row.get('status','')),'remark':bm_row.get('remark',''),'activity_dt':bm_row.get('activity_dt','')})
                    try:
                        report_machine=machine_row(bm_code)
                    except Exception:
                        continue
                    report_pdf=build_breakdown_report_pdf(report_job,report_breakdown,report_machine)
                    safe_job=re.sub(r'[^A-Za-z0-9_-]+','-',bm_job_id).strip('-') or f'row-{row_number}'
                    report_file=f'Breakdown_Report_{safe_job}.pdf'
                    bm_zip.writestr(report_file,report_pdf)
                    p1,p2,p3=st.columns([1.5,2.5,1.2])
                    p1.write(bm_code); p2.code(bm_job_id)
                    p3.download_button('⬇️ PDF',data=report_pdf,file_name=report_file,mime='application/pdf',key=f'bm_history_pdf_{safe_job}_{row_number}',on_click='ignore',use_container_width=True)
            bm_zip_buffer.seek(0)
            dl2.download_button('📦 Download Breakdown PDFs (ZIP)',data=bm_zip_buffer.getvalue(),file_name=f'AQPL_Breakdown_Reports_{bm_report_from.strftime(\"%Y%m%d\")}_{bm_report_to.strftime(\"%Y%m%d\")}.zip',mime='application/zip',key=f'bm_report_zip_{bm_report_from}_{bm_report_to}_{bm_report_machine}',use_container_width=True)

with T[4]:"""
source,_bm_history_count=_runtime_re.subn(_bm_history_pattern,_bm_history_repl,source,count=1)
if _bm_history_count!=1:
    raise RuntimeError('AQPL Breakdown History search block could not be injected into legacy_app.py')

_daily_history_pattern=r"(?s)    st\.markdown\('### 📚 Saved Daily Work'\); daily=daily_log_frame\(\)\n    if daily\.empty:st\.info\('अभी कोई Daily Work entry saved नहीं है।'\)\n    else:\n.*?        st\.markdown\('#### ✏️ Edit / Delete Saved Entry'\)"
_daily_history_repl="""    st.markdown('### 📚 Saved Daily Work — Search & Download')
    daily=daily_log_frame()
    if daily.empty:
        st.info('अभी कोई Daily Work entry saved नहीं है।')
    else:
        st.caption('Machine, date range, work type और status से historical daily work search करें।')
        f1,f2,f3,f4,f5=st.columns(5)
        daily_from=f1.date_input('From Date',value=TODAY.replace(day=1),key='daily_report_from')
        daily_to=f2.date_input('To Date',value=TODAY,key='daily_report_to')
        machine_filter=f3.selectbox('Machine Filter',['ALL']+sorted(daily['Machine Code'].dropna().astype(str).unique().tolist()),key='daily_report_machine')
        type_filter=f4.selectbox('Work Type Filter',['ALL']+sorted(daily['Work Type'].dropna().astype(str).unique().tolist()),key='daily_report_type')
        status_filter=f5.selectbox('Status Filter',['ALL']+sorted(daily['Work Status'].dropna().astype(str).unique().tolist()),key='daily_report_status')
        if daily_from>daily_to:
            st.error('From Date cannot be after To Date.')
            filtered=daily.iloc[0:0].copy()
        else:
            filtered=daily.copy()
            filtered['_date']=pd.to_datetime(filtered['Date'],errors='coerce').dt.date
            filtered=filtered[(filtered['_date']>=daily_from)&(filtered['_date']<=daily_to)]
            if machine_filter!='ALL': filtered=filtered[filtered['Machine Code'].astype(str)==machine_filter]
            if type_filter!='ALL': filtered=filtered[filtered['Work Type'].astype(str)==type_filter]
            if status_filter!='ALL': filtered=filtered[filtered['Work Status'].astype(str)==status_filter]
        if filtered.empty:
            st.info('Selected filter में कोई Daily Work record नहीं मिला।')
        else:
            daily_display=filtered.drop(columns=['ID','_date'],errors='ignore')
            st.success(f'{len(daily_display)} Daily Work record(s) found.')
            st.dataframe(daily_display,use_container_width=True,hide_index=True)
            st.download_button('⬇️ Download Filtered Daily Work CSV',data=daily_display.to_csv(index=False).encode('utf-8-sig'),file_name=f'Daily_Maintenance_Work_{daily_from.strftime(\"%Y%m%d\")}_{daily_to.strftime(\"%Y%m%d\")}.csv',mime='text/csv',key=f'daily_work_csv_{daily_from}_{daily_to}_{machine_filter}_{type_filter}_{status_filter}',use_container_width=True)
        st.markdown('#### ✏️ Edit / Delete Saved Entry')"""
source,_daily_history_count=_runtime_re.subn(_daily_history_pattern,_daily_history_repl,source,count=1)
if _daily_history_count!=1:
    raise RuntimeError('AQPL Daily Work history search block could not be injected into legacy_app.py')

_machine_history_old="""    history_view=q('select job_id,maintenance_type,start_dt,problem,action_taken,restart_dt,remark from history where machine_code=? and maintenance_type=? order by id desc',(code,activity_type)); st.dataframe(history_view,use_container_width=True,hide_index=True)"""
_machine_history_new="""    hf1,hf2=st.columns(2)
    history_from=hf1.date_input('History From Date',value=TODAY.replace(day=1),key=f'{history_key}_from_date')
    history_to=hf2.date_input('History To Date',value=TODAY,key=f'{history_key}_to_date')
    history_view=q('select job_id,maintenance_type,start_dt,problem,action_taken,restart_dt,remark from history where machine_code=? and maintenance_type=? order by id desc',(code,activity_type))
    if history_from>history_to:
        st.error('History From Date cannot be after To Date.')
        history_view=history_view.iloc[0:0].copy()
    elif not history_view.empty:
        history_view=history_view.copy()
        history_view['_start_date']=pd.to_datetime(history_view['start_dt'],errors='coerce').dt.date
        history_view=history_view[(history_view['_start_date']>=history_from)&(history_view['_start_date']<=history_to)].drop(columns=['_start_date'])
    if history_view.empty:
        st.info('Selected machine, activity type और date range में saved history नहीं मिली।')
    else:
        st.success(f'{len(history_view)} {activity_type} history record(s) found for {code}.')
        st.dataframe(history_view,use_container_width=True,hide_index=True)"""
if _machine_history_old not in source:
    raise RuntimeError('AQPL Machine History filter anchor was not found in legacy_app.py')
source=source.replace(_machine_history_old,_machine_history_new,1)

_breakdown_report_old="""    saved_breakdowns=q('select * from breakdowns where machine_code=? order by id desc',(code,))"""
_breakdown_report_new="""    brf1,brf2=st.columns(2)
    breakdown_report_from=brf1.date_input('Report From Date',value=TODAY.replace(day=1),key=f'bd_report_from_{code}')
    breakdown_report_to=brf2.date_input('Report To Date',value=TODAY,key=f'bd_report_to_{code}')
    saved_breakdowns=q('select * from breakdowns where machine_code=? order by id desc',(code,))
    if breakdown_report_from>breakdown_report_to:
        st.error('Report From Date cannot be after To Date.')
        saved_breakdowns=saved_breakdowns.iloc[0:0].copy()
    elif not saved_breakdowns.empty:
        bm_jobs_for_dates=q(\"select job_id,opened_at from jobs where job_type='BM' order by opened_at desc\")
        opened_by_job={str(row.job_id):row.opened_at for _,row in bm_jobs_for_dates.iterrows()} if not bm_jobs_for_dates.empty else {}
        saved_breakdowns=saved_breakdowns.copy()
        saved_breakdowns['_report_dt']=pd.to_datetime(saved_breakdowns['job_id'].astype(str).map(opened_by_job),errors='coerce')
        saved_breakdowns=saved_breakdowns[(saved_breakdowns['_report_dt'].dt.date>=breakdown_report_from)&(saved_breakdowns['_report_dt'].dt.date<=breakdown_report_to)]
    if not saved_breakdowns.empty:
        history_preview=saved_breakdowns[['job_id','_report_dt','failure','downtime_hr','status']].copy()
        history_preview['_report_dt']=history_preview['_report_dt'].dt.strftime('%d-%m-%Y')
        history_preview=history_preview.rename(columns={'job_id':'Job ID','_report_dt':'Breakdown Date','failure':'Problem / Failure','downtime_hr':'Downtime Hr','status':'Status'})
        st.success(f'{len(history_preview)} saved Breakdown Report(s) found for {code}.')
        st.dataframe(history_preview,use_container_width=True,hide_index=True)"""
if _breakdown_report_old not in source:
    raise RuntimeError('AQPL Breakdown report filter anchor was not found in legacy_app.py')
source=source.replace(_breakdown_report_old,_breakdown_report_new,1)

runtime_globals={'__name__':'__main__','__file__':str(DASHBOARD_SCRIPT),'__package__':None,'__cached__':None}
exec(compile(source,str(DASHBOARD_SCRIPT),'exec'),runtime_globals)
