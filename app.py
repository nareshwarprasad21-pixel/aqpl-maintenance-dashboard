"""AQPL Maintenance Dashboard entrypoint with runtime enhancements."""
from pathlib import Path

DASHBOARD_SCRIPT = Path(__file__).with_name("legacy_app.py")
source = DASHBOARD_SCRIPT.read_text(encoding="utf-8")

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

# Add an ALL MACHINES option to the PM page for monthly/date-range document downloads.
pm_code_old="""    st.subheader('Preventive Maintenance Check Sheet'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode'); mr=machine_row(code); sheet=resolve_checklist(code,mr)"""
pm_code_new="""    st.subheader('Preventive Maintenance Check Sheet'); code=st.selectbox('Machine Code',['ALL MACHINES']+MACH.machine_code.tolist(),key='pmcode')
    if code=='ALL MACHINES':
        st.markdown('### 📚 All Machines PM Check Sheets - Download / Print')
        st.caption('Select a month/date range to collect saved PM documents for every machine. This view is download/history only; PM entry remains machine-specific.')
        af1,af2,af3=st.columns([1,1,1])
        all_from=af1.date_input('From Date',value=TODAY.replace(day=1),key='all_pm_from')
        all_to=af2.date_input('To Date',value=TODAY,key='all_pm_to')
        all_search=af3.button('🔎 Search All Machines',key='all_pm_search',use_container_width=True)
        if all_search:
            if all_from>all_to: st.error('From Date cannot be after To Date.')
            else: st.session_state['all_pm_range']=(all_from,all_to)
        range_from,range_to=st.session_state.get('all_pm_range',(all_from,all_to))
        all_jobs=q(\"select * from jobs where job_type='PM' order by opened_at,machine_code\")
        if not all_jobs.empty:
            all_jobs=all_jobs.copy(); all_jobs['_maintenance_dt']=pd.to_datetime(all_jobs['opened_at'],errors='coerce')
            all_jobs=all_jobs[(all_jobs['_maintenance_dt'].dt.date>=range_from)&(all_jobs['_maintenance_dt'].dt.date<=range_to)]
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
        st.stop()
    mr=machine_row(code); sheet=resolve_checklist(code,mr)"""
if pm_code_old in source: source=source.replace(pm_code_old,pm_code_new,1)

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

# Daily Work Log: allow Start Time and End Time editing and recalculate Total Time.
daily_edit_old="""        with st.form(f'daily_edit_{selected_daily}'):
            e1,e2=st.columns(2); edit_problem=e1.text_area('Problem / Observation',value=str(selected_row['Problem / Observation'])); edit_action=e2.text_area('Work Done / Action Taken',value=str(selected_row['Work Done']))
            e3,e4,e5=st.columns(3); edit_team=e3.text_input('Team Members',value=str(selected_row['Team Members'])); statuses=['Completed','Pending','In Progress','Temporary Solution']; edit_status=e4.selectbox('Work Status',statuses,index=statuses.index(selected_row['Work Status']) if selected_row['Work Status'] in statuses else 0); edit_pending=e5.text_input('Pending Action',value=str(selected_row['Pending Action']))
            edit_remarks=st.text_area('Remarks',value=str(selected_row['Remarks'])); update_daily=st.form_submit_button('💾 Update Entry',type='primary')
        if update_daily:
            history_row=q('select remark from history where job_id=?',(selected_daily,)).iloc[0]; meta=daily_log_details(history_row.remark); meta.update({'team_members':edit_team.strip(),'work_status':edit_status,'pending_action':edit_pending.strip(),'remarks':edit_remarks.strip()})
            execsql('update history set problem=?,action_taken=?,remark=? where job_id=?',(edit_problem.strip(),edit_action.strip(),DAILY_LOG_PREFIX+json.dumps(meta,ensure_ascii=False),selected_daily)); execsql('update jobs set problem=?,status=? where job_id=?',(edit_problem.strip(),edit_status.upper(),selected_daily)); st.success(f'{selected_daily} updated successfully.'); st.rerun()
"""
daily_edit_new="""        history_edit_row=q('select start_dt,restart_dt,remark from history where job_id=?',(selected_daily,)).iloc[0]
        old_start=pd.to_datetime(history_edit_row.start_dt,errors='coerce'); old_end=pd.to_datetime(history_edit_row.restart_dt,errors='coerce')
        if pd.isna(old_start): old_start=datetime.combine(TODAY,datetime.now().time().replace(second=0,microsecond=0))
        if pd.isna(old_end): old_end=old_start
        with st.form(f'daily_edit_{selected_daily}'):
            e1,e2=st.columns(2); edit_problem=e1.text_area('Problem / Observation',value=str(selected_row['Problem / Observation'])); edit_action=e2.text_area('Work Done / Action Taken',value=str(selected_row['Work Done']))
            t1,t2=st.columns(2); edit_start_time=t1.time_input('Start Time',value=old_start.time().replace(second=0,microsecond=0)); edit_end_time=t2.time_input('End Time',value=old_end.time().replace(second=0,microsecond=0))
            e3,e4,e5=st.columns(3); edit_team=e3.text_input('Team Members',value=str(selected_row['Team Members'])); statuses=['Completed','Pending','In Progress','Temporary Solution']; edit_status=e4.selectbox('Work Status',statuses,index=statuses.index(selected_row['Work Status']) if selected_row['Work Status'] in statuses else 0); edit_pending=e5.text_input('Pending Action',value=str(selected_row['Pending Action']))
            edit_remarks=st.text_area('Remarks',value=str(selected_row['Remarks'])); update_daily=st.form_submit_button('💾 Update Entry',type='primary')
        if update_daily:
            edit_start_dt=datetime.combine(old_start.date(),edit_start_time); edit_end_dt=datetime.combine(old_end.date(),edit_end_time)
            if edit_end_dt<edit_start_dt:
                st.error('End Time cannot be earlier than Start Time.')
            else:
                total_minutes=int((edit_end_dt-edit_start_dt).total_seconds()//60); total_hours,total_mins=divmod(total_minutes,60); edit_total_time=f'{total_hours}h {total_mins}m'
                meta=daily_log_details(history_edit_row.remark); meta.update({'team_members':edit_team.strip(),'work_status':edit_status,'pending_action':edit_pending.strip(),'remarks':edit_remarks.strip(),'total_time':edit_total_time})
                start_iso=edit_start_dt.isoformat(timespec='minutes'); end_iso=edit_end_dt.isoformat(timespec='minutes')
                execsql('update history set start_dt=?,problem=?,action_taken=?,restart_dt=?,remark=? where job_id=?',(start_iso,edit_problem.strip(),edit_action.strip(),end_iso,DAILY_LOG_PREFIX+json.dumps(meta,ensure_ascii=False),selected_daily)); execsql('update jobs set problem=?,status=? where job_id=?',(edit_problem.strip(),edit_status.upper(),selected_daily)); st.success(f'{selected_daily} updated successfully. Total time: {edit_total_time}.'); st.rerun()
"""
if daily_edit_old in source: source=source.replace(daily_edit_old,daily_edit_new,1)

runtime_globals={'__name__':'__main__','__file__':str(DASHBOARD_SCRIPT),'__package__':None,'__cached__':None}
exec(compile(source,str(DASHBOARD_SCRIPT),'exec'),runtime_globals)
