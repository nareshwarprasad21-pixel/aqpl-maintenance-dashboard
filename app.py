"""AQPL Maintenance Dashboard entrypoint.

Run the proven dashboard script on every Streamlit rerun. Importing
``legacy_app`` normally is intentionally avoided because Python caches imported
modules; after the first render, a Streamlit reconnect/rerun could otherwise
produce a blank page until the app process was rebooted.

This entrypoint also applies small, isolated UI enhancements at runtime:
- PM Action and Remark fields become searchable suggestion boxes.
- Daily Work Log mapped-machine selection starts blank so the user must choose.
- Date-wise history search + Excel/PDF downloads are available in PM, BM,
  Daily Work Log, Machine History and Breakdown History tabs.
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

# Daily Work Log: do not preselect the first mapped machine. Keeping index=None
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
# still blank. Show a clear validation message instead.
daily_validation_old = """        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""

daily_validation_new = """        elif daily_code is None:st.error('Please select a Machine before saving the Daily Work Entry.')
        elif daily_code in ['__MISC__','__FACILITY__'] and not misc_machine_name.strip():st.error('Manual/Facility entry के लिए Machine / Equipment Name या Work Area required है।')
        else:
"""

if daily_validation_old in source:
    source = source.replace(daily_validation_old, daily_validation_new, 1)

# Shared date-wise history search and export helper. It is injected into the
# legacy script so every relevant tab can reuse exactly the same mobile-friendly UI.
history_helper = r'''
def _aqpl_history_source(kind):
    if kind == 'PM':
        df=q('select * from pm_checks order by id desc')
        return df,'created_at','Preventive Maintenance History'
    if kind == 'BM':
        df=q('select * from history order by id desc')
        if len(df) and 'maintenance_type' in df.columns:
            df=df[df['maintenance_type'].astype(str).str.upper()=='BM']
        return df,'start_dt','Breakdown Maintenance History'
    if kind == 'DAILY':
        df=q('select * from history order by id desc')
        if len(df) and 'maintenance_type' in df.columns:
            df=df[df['maintenance_type'].astype(str).str.upper()=='DAILY']
        return df,'start_dt','Daily Maintenance Work History'
    if kind == 'MACHINE':
        return q('select * from history order by id desc'),'start_dt','Machine Maintenance History'
    if kind == 'BDH':
        return q('select * from breakdown_activity_log order by id desc'),'activity_dt','Breakdown Activity History'
    return pd.DataFrame(),None,'Maintenance History'


def _aqpl_excel_bytes(df,sheet_name='History'):
    output=BytesIO()
    safe_name=re.sub(r'[^A-Za-z0-9 _-]+','',sheet_name)[:31] or 'History'
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        df.to_excel(writer,index=False,sheet_name=safe_name)
    output.seek(0)
    return output.getvalue()


def _aqpl_pdf_bytes(df,title,date_text):
    output=BytesIO()
    regular='Helvetica'; bold='Helvetica-Bold'
    regular_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont('AQPLSearchSans',regular_path))
            pdfmetrics.registerFont(TTFont('AQPLSearchSansBold',bold_path))
            regular='AQPLSearchSans'; bold='AQPLSearchSansBold'
        except Exception:
            pass
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle('AQPLSearchTitle',parent=styles['Heading2'],fontName=bold,fontSize=13,leading=16,spaceAfter=5*mm)
    body_style=ParagraphStyle('AQPLSearchBody',parent=styles['BodyText'],fontName=regular,fontSize=7.5,leading=10,spaceAfter=1.8*mm)
    doc=SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm)
    story=[Paragraph(escape(title),title_style),Paragraph(escape(date_text),body_style),Spacer(1,2*mm)]
    if df.empty:
        story.append(Paragraph('No records found.',body_style))
    else:
        for n,(_,row) in enumerate(df.iterrows(),1):
            values=[]
            for col,val in row.items():
                if pd.isna(val):
                    continue
                txt=str(val).strip()
                if not txt or txt.lower()=='nan':
                    continue
                values.append(f'<b>{escape(str(col))}:</b> {escape(txt)}')
            story.append(Paragraph(f'<b>Record {n}</b> &nbsp; ' + ' &nbsp; | &nbsp; '.join(values),body_style))
            story.append(Spacer(1,1.5*mm))
    doc.build(story)
    return output.getvalue()


def render_datewise_history(kind,key_prefix,default_machine=None):
    df,date_col,title=_aqpl_history_source(kind)
    with st.expander('🔎 Search History / Download Records',expanded=False):
        if df.empty or not date_col or date_col not in df.columns:
            st.info('No saved history is available yet.')
            return

        data=df.copy()
        data['_aqpl_dt']=pd.to_datetime(data[date_col],errors='coerce')
        valid_dates=data['_aqpl_dt'].dropna()
        today=date.today()
        earliest=valid_dates.min().date() if len(valid_dates) else today
        latest=valid_dates.max().date() if len(valid_dates) else today

        preset=st.selectbox(
            'Date Range',
            ['Today','Yesterday','This Week','This Month','Last Month','Custom Range','All Records'],
            index=3,
            key=f'{key_prefix}_date_preset'
        )
        if preset=='Today':
            from_date=to_date=today
        elif preset=='Yesterday':
            from_date=to_date=today-timedelta(days=1)
        elif preset=='This Week':
            from_date=today-timedelta(days=today.weekday()); to_date=today
        elif preset=='This Month':
            from_date=today.replace(day=1); to_date=today
        elif preset=='Last Month':
            first_this=today.replace(day=1)
            to_date=first_this-timedelta(days=1); from_date=to_date.replace(day=1)
        elif preset=='All Records':
            from_date=earliest; to_date=max(latest,today)
        else:
            c1,c2=st.columns(2)
            from_date=c1.date_input('From Date',value=today.replace(day=1),key=f'{key_prefix}_from')
            to_date=c2.date_input('To Date',value=today,key=f'{key_prefix}_to')

        if from_date>to_date:
            st.error('From Date cannot be after To Date.')
            return

        filtered=data[(data['_aqpl_dt'].dt.date>=from_date)&(data['_aqpl_dt'].dt.date<=to_date)].copy()

        machine_col='machine_code' if 'machine_code' in filtered.columns else None
        if machine_col:
            machines=['All Machines']+sorted([x for x in data[machine_col].dropna().astype(str).unique().tolist() if x.strip()])
            default_index=0
            if default_machine and str(default_machine) in machines:
                default_index=machines.index(str(default_machine))
            machine_choice=st.selectbox('Machine',machines,index=default_index,key=f'{key_prefix}_machine_filter')
            if machine_choice!='All Machines':
                filtered=filtered[filtered[machine_col].astype(str)==machine_choice]

        if kind=='MACHINE' and 'maintenance_type' in filtered.columns:
            activity=st.multiselect('Activity Type',['PM','BM','DAILY'],default=['PM','BM','DAILY'],key=f'{key_prefix}_activity')
            if activity:
                filtered=filtered[filtered['maintenance_type'].astype(str).str.upper().isin(activity)]
            else:
                filtered=filtered.iloc[0:0]

        search_text=st.text_input('Search Job ID / Problem / Action / Remark',placeholder='Optional keyword',key=f'{key_prefix}_keyword').strip()
        if search_text and len(filtered):
            searchable=filtered.drop(columns=['_aqpl_dt'],errors='ignore').fillna('').astype(str)
            mask=searchable.apply(lambda col: col.str.contains(search_text,case=False,na=False,regex=False)).any(axis=1)
            filtered=filtered[mask]

        display=filtered.drop(columns=['_aqpl_dt'],errors='ignore')
        st.caption(f'{from_date:%d-%m-%Y} to {to_date:%d-%m-%Y} • {len(display)} record(s) found')
        if len(display):
            st.dataframe(display,use_container_width=True,hide_index=True)
            export_name=re.sub(r'[^A-Za-z0-9_-]+','_',title).strip('_')
            machine_suffix=''
            if machine_col and 'machine_choice' in locals() and machine_choice!='All Machines':
                machine_suffix='_'+re.sub(r'[^A-Za-z0-9_-]+','_',machine_choice)
            base=f'{export_name}{machine_suffix}_{from_date:%Y%m%d}_{to_date:%Y%m%d}'
            excel_bytes=_aqpl_excel_bytes(display,title[:31])
            pdf_bytes=_aqpl_pdf_bytes(display,title,f'Date Range: {from_date:%d-%m-%Y} to {to_date:%d-%m-%Y}')
            d1,d2=st.columns(2)
            d1.download_button('📥 Download Excel',data=excel_bytes,file_name=base+'.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'{key_prefix}_xlsx')
            d2.download_button('📄 Download PDF',data=pdf_bytes,file_name=base+'.pdf',mime='application/pdf',key=f'{key_prefix}_pdf')
        else:
            st.info('Selected filters में कोई history record नहीं मिला।')
'''

# Insert helper immediately before tabs are created, where q(), DB tables and
# reportlab imports are already available.
tabs_anchor = "T=st.tabs(['🏠 Dashboard','📅 PM Plan','✅ PM Check Sheet','🚨 Breakdown','📋 Daily Job Plan','📝 Daily Work Log','🗂️ Machine History','📋 Breakdown History','🧾 Work Orders & Permits','🔎 Why-Why Analysis','⚙️ Equipment Master','🔗 Checklist Mapping'])"
if tabs_anchor in source and 'def render_datewise_history(' not in source:
    source=source.replace(tabs_anchor,history_helper+'\n'+tabs_anchor,1)

# Add the shared search/download UI to the five requested tabs.
pm_anchor="""with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
"""
pm_repl="""with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
    render_datewise_history('PM','pm_hist_search',code)
"""
if pm_anchor in source:
    source=source.replace(pm_anchor,pm_repl,1)

bm_anchor="""with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f\"{mr.machine_name} | {mr.location} | {mr.make_model}\")
"""
bm_repl="""with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f\"{mr.machine_name} | {mr.location} | {mr.make_model}\")
    render_datewise_history('BM','bm_hist_search',code)
"""
if bm_anchor in source:
    source=source.replace(bm_anchor,bm_repl,1)

daily_anchor="""with T[5]:
    st.subheader('📝 Daily Maintenance Work Log')
    st.caption('Maintenance team ने दिनभर किस machine पर क्या काम किया—यहाँ record करें। Equipment Master की machine चुनें या Miscellaneous / Other Machine में नाम खुद लिखें।')
"""
daily_repl="""with T[5]:
    st.subheader('📝 Daily Maintenance Work Log')
    st.caption('Maintenance team ने दिनभर किस machine पर क्या काम किया—यहाँ record करें। Equipment Master की machine चुनें या Miscellaneous / Other Machine में नाम खुद लिखें।')
    render_datewise_history('DAILY','daily_hist_search')
"""
if daily_anchor in source:
    source=source.replace(daily_anchor,daily_repl,1)

machine_anchor="""with T[6]:
    st.subheader('Machine History Card — PM/BM'); code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}'); daily_linked=q(\"select job_id,start_dt,problem,action_taken,restart_dt from history where machine_code=? and maintenance_type='DAILY' order by id desc\",(code,)); st.markdown('### 📝 Daily Work / Completed Job Plan History'); st.dataframe(daily_linked,use_container_width=True,hide_index=True) if len(daily_linked) else st.info('इस machine की Daily Work / completed Job Plan history अभी नहीं है।'); activity_type=st.radio('Maintenance Activity Type',['PM','BM'],horizontal=True,key='hist_activity_type'); st.caption('Select PM for Preventive Maintenance or BM for Breakdown Maintenance. You can add a new history entry below.'); st.markdown('### ➕ Fill / Add Maintenance History'); default_jid=new_id(activity_type)
"""
machine_repl="""with T[6]:
    st.subheader('Machine History Card — PM/BM'); code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}'); render_datewise_history('MACHINE','machine_hist_search',code); daily_linked=q(\"select job_id,start_dt,problem,action_taken,restart_dt from history where machine_code=? and maintenance_type='DAILY' order by id desc\",(code,)); st.markdown('### 📝 Daily Work / Completed Job Plan History'); st.dataframe(daily_linked,use_container_width=True,hide_index=True) if len(daily_linked) else st.info('इस machine की Daily Work / completed Job Plan history अभी नहीं है।'); activity_type=st.radio('Maintenance Activity Type',['PM','BM'],horizontal=True,key='hist_activity_type'); st.caption('Select PM for Preventive Maintenance or BM for Breakdown Maintenance. You can add a new history entry below.'); st.markdown('### ➕ Fill / Add Maintenance History'); default_jid=new_id(activity_type)
"""
if machine_anchor in source:
    source=source.replace(machine_anchor,machine_repl,1)

bdh_anchor="""with T[7]:
    st.subheader('Breakdown History Card — Editable Activity Log')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
"""
bdh_repl="""with T[7]:
    st.subheader('Breakdown History Card — Editable Activity Log')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
    render_datewise_history('BDH','bdh_hist_search',code)
"""
if bdh_anchor in source:
    source=source.replace(bdh_anchor,bdh_repl,1)

# Execute with the real legacy file path so its existing __file__ based paths
# (database, data files, logo assets, etc.) keep working exactly as before.
runtime_globals = {
    "__name__": "__main__",
    "__file__": str(DASHBOARD_SCRIPT),
    "__package__": None,
    "__cached__": None,
}
exec(compile(source, str(DASHBOARD_SCRIPT), "exec"), runtime_globals)
