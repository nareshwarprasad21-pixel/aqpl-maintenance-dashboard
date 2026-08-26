from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_form = """        remark=st.text_area('Remark / Observation',key=f'{history_key}_remark')
        start_dt_value=datetime.combine(start_date,start_time); restart_dt_value=datetime.combine(restart_date,restart_time); duration_seconds=(restart_dt_value-start_dt_value).total_seconds(); valid_history_time=duration_seconds>=0; downtime=round(max(duration_seconds,0)/3600,2); total_history_minutes=int(max(duration_seconds,0)//60); history_hours,history_minutes=divmod(total_history_minutes,60)
"""
new_form = """        remark=st.text_area('Remark / Observation',key=f'{history_key}_remark')
        st.markdown('#### 🦺 Safety / Permit Requirement')
        st.caption('Job में welding/cutting/grinding हो तो Hot Work चुनें; height पर काम हो तो Work at Height चुनें. दोनों hazards हों तो दोनों permits बनेंगे।')
        p1,p2=st.columns(2)
        hot=p1.checkbox('🔥 Hot Work — Welding / Cutting / Grinding',key=f'{history_key}_hot')
        height=p2.checkbox('🪜 Work at Height',key=f'{history_key}_height')
        if hot and height:
            st.warning('Hot Work Permit + Height Work Permit — दोनों required हैं। Save करने पर दोनों permit drafts इस Job ID से link होंगे।')
        elif hot:
            st.info('Hot Work Permit required. Save करने पर Hot Work Permit draft इस Job ID से link होगा।')
        elif height:
            st.info('Height Work Permit required. Save करने पर Height Work Permit draft इस Job ID से link होगा।')
        else:
            st.caption('Normal maintenance: Hot/Height permit selected नहीं है।')
        start_dt_value=datetime.combine(start_date,start_time); restart_dt_value=datetime.combine(restart_date,restart_time); duration_seconds=(restart_dt_value-start_dt_value).total_seconds(); valid_history_time=duration_seconds>=0; downtime=round(max(duration_seconds,0)/3600,2); total_history_minutes=int(max(duration_seconds,0)//60); history_hours,history_minutes=divmod(total_history_minutes,60)
"""
if old_form not in text:
    raise SystemExit('Form anchor not found; app.py has changed.')
text = text.replace(old_form, new_form, 1)

old_save = """            start_dt=start_dt_value.isoformat(timespec='minutes'); restart_dt=restart_dt_value.isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,activity_type,code,mr.machine_name,mr.location,start_dt,problem,'CLOSED',0,0,restart_dt)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,activity_type,start_dt,problem,action,restart_dt,remark))
            if activity_type=='BM':
"""
new_save = """            start_dt=start_dt_value.isoformat(timespec='minutes'); restart_dt=restart_dt_value.isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,activity_type,code,mr.machine_name,mr.location,start_dt,problem,'CLOSED',int(hot),int(height),restart_dt)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,activity_type,start_dt,problem,action,restart_dt,remark))
            existing_hot=q('select id from permits where job_id=? and permit_type=?',(jid,'HOT WORK'))
            existing_height=q('select id from permits where job_id=? and permit_type=?',(jid,'HEIGHT WORK'))
            if hot and not len(existing_hot):execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,problem,'DRAFT'))
            if height and not len(existing_height):execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,problem,'DRAFT'))
            permit_note=[]
            if hot:permit_note.append('Hot Work Permit')
            if height:permit_note.append('Height Work Permit')
            permit_text=(' + '.join(permit_note)+' draft linked automatically') if permit_note else 'No Hot/Height permit selected'
            if activity_type=='BM':
"""
if old_save not in text:
    raise SystemExit('Save anchor not found; app.py has changed.')
text = text.replace(old_save, new_save, 1)

old_bm_success = """                st.success(f'BM history saved for {mr.machine_name}. Breakdown History and Why-Why draft also linked automatically. Job ID: {jid}')
            else:st.success(f'PM history saved for {mr.machine_name}. Job ID: {jid}')
"""
new_bm_success = """                st.success(f'BM history saved for {mr.machine_name}. Breakdown History + Why-Why draft linked. Safety: {permit_text}. Job ID: {jid}')
            else:st.success(f'PM history saved for {mr.machine_name}. Safety: {permit_text}. Job ID: {jid}')
"""
if old_bm_success not in text:
    raise SystemExit('Success-message anchor not found; app.py has changed.')
text = text.replace(old_bm_success, new_bm_success, 1)

path.write_text(text, encoding='utf-8')
print('Machine History hot/height permit logic patched successfully.')
