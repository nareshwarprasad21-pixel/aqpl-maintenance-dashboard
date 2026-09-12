"""AQPL Maintenance Dashboard entrypoint with runtime enhancements."""
from pathlib import Path

DASHBOARD_SCRIPT = Path(__file__).with_name("legacy_app.py")
source = DASHBOARD_SCRIPT.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# 1) PM Action / Remark saved sentence suggestions
# ---------------------------------------------------------------------------
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
new_block = """        pm_suggestion_history=q('select check_point,action,remark from pm_checks where machine_code=? order by id desc',(code,))

        def pm_saved_suggestions(check_point,field_name,limit=8):
            if pm_suggestion_history.empty or field_name not in pm_suggestion_history.columns:return []
            key=str(check_point).strip().casefold()
            rows=pm_suggestion_history[pm_suggestion_history['check_point'].fillna('').astype(str).str.strip().str.casefold()==key]
            out=[]; seen=set()
            for value in rows[field_name].tolist():
                text='' if value is None else str(value).strip(); norm=text.casefold()
                if not text or norm in ('nan','none') or norm in seen:continue
                seen.add(norm); out.append(text)
                if len(out)>=limit:break
            return out

        results=[]
        with st.form(f'pmform_{pm_key}'):
            h1,h2,h3,h4,h5=st.columns([0.7,4.6,2,3.4,3.4])
            h1.markdown('**S.No.**'); h2.markdown('**Check Points**'); h3.markdown('**Status**'); h4.markdown('**Actions**'); h5.markdown('**Remarks**')
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c,d,e=st.columns([0.7,4.6,2,3.4,3.4]); a.write(i); b.write(pt)
                status=c.selectbox('Status',['OK','NOT OK','N/A'],key=f'{pm_key}_s{i}',label_visibility='collapsed')
                action_txt=d.selectbox('Action',pm_saved_suggestions(pt,'action'),index=None,key=f'{pm_key}_a{i}',label_visibility='collapsed',placeholder='Previous action / type new',accept_new_options=True) or ''
                remark=e.selectbox('Remark',pm_saved_suggestions(pt,'remark'),index=None,key=f'{pm_key}_r{i}',label_visibility='collapsed',placeholder='Previous observation / type new',accept_new_options=True) or ''
                results.append((pt,status,action_txt,remark))
"""
if old_block in source: source=source.replace(old_block,new_block,1)

# ---------------------------------------------------------------------------
# 2) Daily Work Log mapped machine starts blank
# ---------------------------------------------------------------------------
old_daily="""            daily_machine_options=MACH.machine_code.tolist()
            daily_code=st.selectbox(
                'Machine',
                daily_machine_options,
                format_func=lambda value:f\"{machine_row(value).machine_name} | {value}\"
            )
            misc_machine_name=''; misc_machine_code=''; misc_location=''
"""
new_daily="""            daily_machine_options=MACH.machine_code.tolist()
            daily_code=st.selectbox('Machine',daily_machine_options,index=None,placeholder='Select Machine',format_func=lambda value:f\"{machine_row(value).machine_name} | {value}\")
            misc_machine_name=''; misc_machine_code=''; misc_location=''
"""
if old_daily in source: source=source.replace(old_daily,new_daily,1)
old_validation="""        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""
new_validation="""        elif daily_code is None:st.error('Please select a Machine before saving the Daily Work Entry.')
        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""
if old_validation in source: source=source.replace(old_validation,new_validation,1)

# ---------------------------------------------------------------------------
# 3) Date-wise history search + Excel/PDF download
# ---------------------------------------------------------------------------
history_helper=r'''
def _aqpl_history_source(kind):
    if kind=='PM': return q('select * from pm_checks order by id desc'),'created_at','Preventive Maintenance History'
    if kind=='BM':
        df=q('select * from history order by id desc')
        if len(df) and 'maintenance_type' in df.columns: df=df[df.maintenance_type.astype(str).str.upper()=='BM']
        return df,'start_dt','Breakdown Maintenance History'
    if kind=='DAILY':
        df=q('select * from history order by id desc')
        if len(df) and 'maintenance_type' in df.columns: df=df[df.maintenance_type.astype(str).str.upper()=='DAILY']
        return df,'start_dt','Daily Maintenance Work History'
    if kind=='MACHINE': return q('select * from history order by id desc'),'start_dt','Machine Maintenance History'
    if kind=='BDH': return q('select * from breakdown_activity_log order by id desc'),'activity_dt','Breakdown Activity History'
    return pd.DataFrame(),None,'Maintenance History'

def _aqpl_excel_bytes(df,sheet_name='History'):
    out=BytesIO(); safe=re.sub(r'[^A-Za-z0-9 _-]+','',sheet_name)[:31] or 'History'
    with pd.ExcelWriter(out,engine='openpyxl') as writer: df.to_excel(writer,index=False,sheet_name=safe)
    out.seek(0); return out.getvalue()

def _aqpl_pdf_bytes(df,title,date_text):
    out=BytesIO(); styles=getSampleStyleSheet()
    ts=ParagraphStyle('AQPLSearchTitle',parent=styles['Heading2'],fontSize=13,leading=16,spaceAfter=5*mm)
    bs=ParagraphStyle('AQPLSearchBody',parent=styles['BodyText'],fontSize=7.5,leading=10,spaceAfter=1.8*mm)
    doc=SimpleDocTemplate(out,pagesize=landscape(A4),leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm)
    story=[Paragraph(escape(title),ts),Paragraph(escape(date_text),bs),Spacer(1,2*mm)]
    if df.empty: story.append(Paragraph('No records found.',bs))
    else:
        for n,(_,row) in enumerate(df.iterrows(),1):
            vals=[]
            for col,val in row.items():
                if pd.isna(val):continue
                text=str(val).strip()
                if not text or text.lower()=='nan':continue
                vals.append(f'<b>{escape(str(col))}:</b> {escape(text)}')
            story.append(Paragraph(f'<b>Record {n}</b> &nbsp; '+' &nbsp; | &nbsp; '.join(vals),bs)); story.append(Spacer(1,1.5*mm))
    doc.build(story); return out.getvalue()

def render_datewise_history(kind,key_prefix,default_machine=None):
    df,date_col,title=_aqpl_history_source(kind)
    with st.expander('🔎 Search History / Download Records',expanded=False):
        if df.empty or not date_col or date_col not in df.columns: st.info('No saved history is available yet.'); return
        data=df.copy(); data['_aqpl_dt']=pd.to_datetime(data[date_col],errors='coerce'); today=date.today()
        valid=data['_aqpl_dt'].dropna(); earliest=valid.min().date() if len(valid) else today; latest=valid.max().date() if len(valid) else today
        preset=st.selectbox('Date Range',['Today','Yesterday','This Week','This Month','Last Month','Custom Range','All Records'],index=3,key=f'{key_prefix}_date_preset')
        if preset=='Today': from_date=to_date=today
        elif preset=='Yesterday': from_date=to_date=today-timedelta(days=1)
        elif preset=='This Week': from_date=today-timedelta(days=today.weekday()); to_date=today
        elif preset=='This Month': from_date=today.replace(day=1); to_date=today
        elif preset=='Last Month':
            first=today.replace(day=1); to_date=first-timedelta(days=1); from_date=to_date.replace(day=1)
        elif preset=='All Records': from_date=earliest; to_date=max(latest,today)
        else:
            c1,c2=st.columns(2); from_date=c1.date_input('From Date',today.replace(day=1),key=f'{key_prefix}_from'); to_date=c2.date_input('To Date',today,key=f'{key_prefix}_to')
        if from_date>to_date: st.error('From Date cannot be after To Date.'); return
        filtered=data[(data['_aqpl_dt'].dt.date>=from_date)&(data['_aqpl_dt'].dt.date<=to_date)].copy(); machine='All Machines'
        if 'machine_code' in data.columns:
            machines=['All Machines']+sorted([x for x in data.machine_code.dropna().astype(str).unique().tolist() if x.strip()])
            idx=machines.index(str(default_machine)) if default_machine and str(default_machine) in machines else 0
            machine=st.selectbox('Machine',machines,index=idx,key=f'{key_prefix}_machine_filter')
            if machine!='All Machines': filtered=filtered[filtered.machine_code.astype(str)==machine]
        if kind=='MACHINE' and 'maintenance_type' in filtered.columns:
            act=st.multiselect('Activity Type',['PM','BM','DAILY'],default=['PM','BM','DAILY'],key=f'{key_prefix}_activity')
            filtered=filtered[filtered.maintenance_type.astype(str).str.upper().isin(act)] if act else filtered.iloc[0:0]
        text=st.text_input('Search Job ID / Problem / Action / Remark',placeholder='Optional keyword',key=f'{key_prefix}_keyword').strip()
        if text and len(filtered):
            searchable=filtered.drop(columns=['_aqpl_dt'],errors='ignore').fillna('').astype(str)
            filtered=filtered[searchable.apply(lambda c:c.str.contains(text,case=False,na=False,regex=False)).any(axis=1)]
        display=filtered.drop(columns=['_aqpl_dt'],errors='ignore'); st.caption(f'{from_date:%d-%m-%Y} to {to_date:%d-%m-%Y} • {len(display)} record(s) found')
        if not len(display): st.info('Selected filters में कोई history record नहीं मिला।'); return
        st.dataframe(display,use_container_width=True,hide_index=True)
        name=re.sub(r'[^A-Za-z0-9_-]+','_',title).strip('_')
        if machine!='All Machines': name+='_'+re.sub(r'[^A-Za-z0-9_-]+','_',machine)
        base=f'{name}_{from_date:%Y%m%d}_{to_date:%Y%m%d}'; d1,d2=st.columns(2)
        d1.download_button('📥 Download Excel',_aqpl_excel_bytes(display,title[:31]),base+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'{key_prefix}_xlsx')
        d2.download_button('📄 Download PDF',_aqpl_pdf_bytes(display,title,f'Date Range: {from_date:%d-%m-%Y} to {to_date:%d-%m-%Y}'),base+'.pdf','application/pdf',key=f'{key_prefix}_pdf')
'''

# ---------------------------------------------------------------------------
# 4) Tabs: use session-state value only as DEFAULT. Do not bind the tab widget
#    to that key, so Quick Access can safely update it after tabs are rendered.
# ---------------------------------------------------------------------------
tabs_anchor="T=st.tabs(['🏠 Dashboard','📅 PM Plan','✅ PM Check Sheet','🚨 Breakdown','📋 Daily Job Plan','📝 Daily Work Log','🗂️ Machine History','📋 Breakdown History','🧾 Work Orders & Permits','🔎 Why-Why Analysis','⚙️ Equipment Master','🔗 Checklist Mapping'])"
tabs_repl=r"""_AQPL_TABS=['🏠 Dashboard','📅 PM Plan','✅ PM Check Sheet','🚨 Breakdown','📋 Daily Job Plan','📝 Daily Work Log','🗂️ Machine History','📋 Breakdown History','🧾 Work Orders & Permits','🔎 Why-Why Analysis','⚙️ Equipment Master','🔗 Checklist Mapping']
_aqpl_default_tab=st.session_state.get('aqpl_main_tab','🏠 Dashboard')
if _aqpl_default_tab not in _AQPL_TABS:_aqpl_default_tab='🏠 Dashboard'
T=st.tabs(_AQPL_TABS,default=_aqpl_default_tab)"""
if tabs_anchor in source: source=source.replace(tabs_anchor,history_helper+'\n'+tabs_repl,1)

# ---------------------------------------------------------------------------
# 5) Add date-wise history UI to requested tabs
# ---------------------------------------------------------------------------
replacements=[
("""with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
""","""with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
    render_datewise_history('PM','pm_hist_search',code)
"""),
("""with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f\"{mr.machine_name} | {mr.location} | {mr.make_model}\")
""","""with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f\"{mr.machine_name} | {mr.location} | {mr.make_model}\")
    render_datewise_history('BM','bm_hist_search',code)
"""),
("""with T[5]:
    st.subheader('📝 Daily Maintenance Work Log')
    st.caption('Maintenance team ने दिनभर किस machine पर क्या काम किया—यहाँ record करें। Equipment Master की machine चुनें या Miscellaneous / Other Machine में नाम खुद लिखें।')
""","""with T[5]:
    st.subheader('📝 Daily Maintenance Work Log')
    st.caption('Maintenance team ने दिनभर किस machine पर क्या काम किया—यहाँ record करें। Equipment Master की machine चुनें या Miscellaneous / Other Machine में नाम खुद लिखें।')
    render_datewise_history('DAILY','daily_hist_search')
"""),
("""with T[6]:
    st.subheader('Machine History Card — PM/BM'); code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}'); daily_linked=q(\"select job_id,start_dt,problem,action_taken,restart_dt from history where machine_code=? and maintenance_type='DAILY' order by id desc\",(code,));""","""with T[6]:
    st.subheader('Machine History Card — PM/BM'); code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}'); render_datewise_history('MACHINE','machine_hist_search',code); daily_linked=q(\"select job_id,start_dt,problem,action_taken,restart_dt from history where machine_code=? and maintenance_type='DAILY' order by id desc\",(code,));"""),
("""with T[7]:
    st.subheader('Breakdown History Card — Editable Activity Log')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
""","""with T[7]:
    st.subheader('Breakdown History Card — Editable Activity Log')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
    render_datewise_history('BDH','bdh_hist_search',code)
""")]
for old,new in replacements:
    if old in source: source=source.replace(old,new,1)

# ---------------------------------------------------------------------------
# 6) Clickable Quick Access cards
# ---------------------------------------------------------------------------
quick_old="""    st.markdown('### ⚡ Quick Access')
    qa1,qa2,qa3,qa4 = st.columns(4)
    qa1.markdown('<div class=\"flow\"><b>🚨 New Breakdown</b><br><span class=\"sub\">Open the Breakdown tab to record failure, downtime and action.</span></div>',unsafe_allow_html=True)
    qa2.markdown('<div class=\"flow\"><b>✅ PM Check Sheet</b><br><span class=\"sub\">Open PM Check Sheet to inspect, save and generate records.</span></div>',unsafe_allow_html=True)
    qa3.markdown('<div class=\"flow\"><b>📝 Daily Work Log</b><br><span class=\"sub\">Record machine-wise maintenance work completed by the team.</span></div>',unsafe_allow_html=True)
    qa4.markdown('<div class=\"flow\"><b>📋 Daily Job Plan</b><br><span class=\"sub\">Review planned, pending and completed maintenance jobs.</span></div>',unsafe_allow_html=True)
"""
quick_new=r"""    st.markdown('### ⚡ Quick Access')
    st.markdown('''<style>
    .st-key-aqpl_quick_access div[data-testid="stButton"] button{min-height:104px!important;text-align:left!important;justify-content:flex-start!important;border:1px solid #2b4564!important;border-radius:12px!important;padding:14px 16px!important;white-space:normal!important;font-size:15px!important;line-height:1.35!important}
    .st-key-aqpl_quick_access div[data-testid="stButton"] button:hover{border-color:#6949e8!important;box-shadow:0 0 0 1px #6949e8 inset!important}
    </style>''',unsafe_allow_html=True)
    with st.container(key='aqpl_quick_access'):
        qa1,qa2,qa3,qa4=st.columns(4)
        if qa1.button('🚨 New Breakdown\n\nRecord failure, downtime and action',use_container_width=True,key='qa_breakdown'):
            st.session_state['aqpl_main_tab']='🚨 Breakdown'; st.rerun()
        if qa2.button('✅ PM Check Sheet\n\nInspect, save and generate PM records',use_container_width=True,key='qa_pm'):
            st.session_state['aqpl_main_tab']='✅ PM Check Sheet'; st.rerun()
        if qa3.button('📝 Daily Work Log\n\nRecord machine-wise completed maintenance work',use_container_width=True,key='qa_daily_work'):
            st.session_state['aqpl_main_tab']='📝 Daily Work Log'; st.rerun()
        if qa4.button('📋 Daily Job Plan\n\nReview planned, pending and completed jobs',use_container_width=True,key='qa_daily_plan'):
            st.session_state['aqpl_main_tab']='📋 Daily Job Plan'; st.rerun()
"""
if quick_old in source: source=source.replace(quick_old,quick_new,1)

runtime_globals={'__name__':'__main__','__file__':str(DASHBOARD_SCRIPT),'__package__':None,'__cached__':None}
exec(compile(source,str(DASHBOARD_SCRIPT),'exec'),runtime_globals)
