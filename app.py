import streamlit as st
import pandas as pd
import sqlite3, json, os, re
from datetime import date, datetime, timedelta

st.set_page_config(page_title='AQPL Maintenance Management', page_icon='🛠️', layout='wide')
BASE=os.path.dirname(__file__); DATA=os.path.join(BASE,'data'); DB=os.path.join(DATA,'maintenance.db')

st.markdown('''<style>
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#07111f,#0b1728);color:#eef4ff}
[data-testid="stSidebar"]{background:#091426;border-right:1px solid #22314b}
.block-container{max-width:1550px;padding-top:1.4rem}.hero{padding:20px 24px;border:1px solid #263958;border-radius:18px;background:linear-gradient(135deg,#10213b,#0b1728);margin-bottom:14px}
.hero h1{margin:0;font-size:2rem}.sub{color:#9fb0c9}.kpi{padding:16px;border-radius:15px;background:#101f35;border:1px solid #243754;min-height:108px}.kpi b{font-size:1.7rem}.green{border-left:5px solid #22c55e}.yellow{border-left:5px solid #eab308}.red{border-left:5px solid #ef4444}.purple{border-left:5px solid #8b5cf6}
.stTabs [data-baseweb="tab-list"]{gap:7px;background:#0d1b30;padding:6px;border-radius:13px}.stTabs [data-baseweb="tab"]{height:44px;padding:0 14px;font-weight:700}.stTabs [aria-selected="true"]{background:#5b43d6;color:white;border-radius:9px}
[data-testid="stDataFrame"],[data-testid="stDataEditor"]{border:1px solid #263958;border-radius:12px;overflow:hidden}.flow{padding:12px 15px;border-radius:12px;background:#101f35;border:1px solid #263958;margin:7px 0}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,[data-testid="stTimeInput"] input{color:#0b1220 !important;background-color:#f8fafc !important;-webkit-text-fill-color:#0b1220 !important;caret-color:#0b1220 !important;font-weight:500}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder{color:#64748b !important;-webkit-text-fill-color:#64748b !important;opacity:1 !important}
[data-testid="stTextInput"] label,[data-testid="stTextArea"] label,[data-testid="stNumberInput"] label,[data-testid="stDateInput"] label,[data-testid="stTimeInput"] label{color:#dbeafe !important}
</style>''',unsafe_allow_html=True)

@st.cache_data
def load_static():
    m=pd.read_csv(os.path.join(DATA,'machines.csv')).fillna('')
    p=pd.read_csv(os.path.join(DATA,'pm_plan.csv')); p['scheduled_date']=pd.to_datetime(p['scheduled_date']).dt.date
    with open(os.path.join(DATA,'checklists.json'),encoding='utf-8') as f:c=json.load(f)
    return m,p,c
MACH,PLAN,CHECKS=load_static()

def conn():
    c=sqlite3.connect(DB,check_same_thread=False)
    c.executescript('''
    CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,job_type TEXT,machine_code TEXT,machine_name TEXT,location TEXT,opened_at TEXT,problem TEXT,status TEXT,hot_work INTEGER,height_work INTEGER,closed_at TEXT);
    CREATE TABLE IF NOT EXISTS pm_checks(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,machine_code TEXT,check_point TEXT,result TEXT,action TEXT,remark TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,machine_code TEXT,maintenance_type TEXT,start_dt TEXT,problem TEXT,action_taken TEXT,restart_dt TEXT,remark TEXT);
    CREATE TABLE IF NOT EXISTS breakdowns(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,machine_code TEXT,failure TEXT,cause TEXT,downtime_hr REAL,spares TEXT,action TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS breakdown_activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,machine_code TEXT,job_id TEXT,activity_dt TEXT,failure TEXT,cause TEXT,action TEXT,spares TEXT,downtime_hr REAL,status TEXT,remark TEXT);
    CREATE TABLE IF NOT EXISTS permits(id INTEGER PRIMARY KEY AUTOINCREMENT,permit_no TEXT,job_id TEXT,permit_type TEXT,machine_code TEXT,activity TEXT,supervisor TEXT,start_dt TEXT,end_dt TEXT,status TEXT,precautions TEXT);
    CREATE TABLE IF NOT EXISTS whywhy(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,machine_code TEXT,problem TEXT,why1 TEXT,why2 TEXT,why3 TEXT,why4 TEXT,why5 TEXT,root_cause TEXT,corrective TEXT,preventive TEXT,owner TEXT,target_date TEXT,effectiveness TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS checklist_map(machine_code TEXT PRIMARY KEY,sheet_name TEXT);
    '''); c.commit(); return c
C=conn()

def q(sql,args=()): return pd.read_sql_query(sql,C,params=args)
def execsql(sql,args=()): C.execute(sql,args); C.commit()
def new_id(kind): return f"AQPL-{kind}-{datetime.now():%Y%m%d-%H%M%S}"
def machine_row(code): return MACH[MACH.machine_code==code].iloc[0]

def suggest_sheet(name):
    n=name.lower(); rules=[('jaw','Jaw crusher'),('secondary cone','sec cone cr'),('tertiary cone','Tertiary cone crusher'),('primary class','Vibro acreen'),('scrubber','scrubber'),('washing class','washing screen'),('de-water','DEWAT.SCREEN'),('heater-1','Heter-1'),('heater-2','Heter-2'),('heater-3','Heter-3'),('primary ball','P.B.MILL'),('secondary ball','S.B.mill'),('primary dynamic','P.Dy.seperator'),('secondary dynamic','S.dy.seprator'),('primary bag','P.baghouse'),('secondary bag','s.baghouse'),('primary vibro','P.vibroscreen'),('secondary vibro','S.vibro screen'),('magnetic','magnetic sep.-1'),('eot crane-1','EOT CRANE-1'),('eot crane-2','EOT CRANE-2'),('eot crane-3','EOT CRAN-3'),('compressor-1','compressor-1'),('compressor-2','compressor-2'),('compressor-3','compressor-3'),('compressor-4','compressor-4'),('chiller-1','chiller-1'),('chiller-2','chiller-2'),('chiller-3','chiller-3')]
    for k,s in rules:
        if k in n:return s
    return ''
def checklist_for(code):
    r=q('select sheet_name from checklist_map where machine_code=?',(code,))
    if len(r) and r.iloc[0,0] in CHECKS:return r.iloc[0,0]
    return suggest_sheet(machine_row(code).machine_name)

def top_header(): st.markdown('<div class="hero"><h1>🛠️ ASIAN QUARTZ PVT LTD — Maintenance Management Dashboard</h1><div class="sub">PM • Breakdown • Machine History • Work Orders • Height/Hot Work Permits • Why-Why RCA</div></div>',unsafe_allow_html=True)
top_header()
TODAY=date.today(); window=TODAY+timedelta(days=7); due=PLAN[PLAN.scheduled_date==TODAY]; overdue=PLAN[PLAN.scheduled_date<TODAY]; hist=q('select * from history'); jobs=q('select * from jobs'); open_bm=jobs[(jobs.job_type=='BM') & (jobs.status!='CLOSED')] if len(jobs) else jobs; open_per=q("select * from permits where status!='CLOSED'"); upcoming=PLAN[(PLAN.scheduled_date>TODAY)&(PLAN.scheduled_date<=window)]
cols=st.columns(5)
for col,title,val,cls in zip(cols,['PM Due Today','PM Next 7 Days','Open Breakdowns','Open Permits','Machine Master'],[len(due),len(upcoming),len(open_bm),len(open_per),len(MACH)],['yellow','purple','red','yellow','green']): col.markdown(f'<div class="kpi {cls}"><span class="sub">{title}</span><br><b>{val}</b></div>',unsafe_allow_html=True)
T=st.tabs(['🏠 Dashboard','📅 PM Plan','✅ PM Check Sheet','🚨 Breakdown','🗂️ Machine History','📋 Breakdown History','🧾 Work Orders & Permits','🔎 Why-Why Analysis','⚙️ Equipment Master','🔗 Checklist Mapping'])

with T[0]:
    st.subheader('Today / Upcoming Maintenance')
    if len(due): st.warning(f'{len(due)} preventive maintenance activities are due today.')
    else: st.success('No PM activity is scheduled exactly for today.')
    st.dataframe(pd.concat([due.assign(Status='DUE TODAY'),upcoming.assign(Status='UPCOMING')]).head(30),use_container_width=True,hide_index=True)
    st.subheader('Linked Workflow'); st.markdown('<div class="flow"><b>PM:</b> PM Plan → Due Alert → Machine Code → PM Check Sheet → Machine History → Close Job / Next Due</div>',unsafe_allow_html=True); st.markdown('<div class="flow"><b>BM:</b> Breakdown → Work Order → Machine History → Breakdown History → Permit(s) if needed → Why-Why RCA → Closure</div>',unsafe_allow_html=True)

with T[1]:
    st.subheader('Preventive Maintenance Plan — 2026–27')
    c1,c2,c3,c4=st.columns([1.05,1.05,1.05,1.35])
    loc=c1.selectbox('Location',['ALL']+sorted(MACH.location.unique().tolist()))
    days=c2.selectbox('Window',['Selected date','All','Due/Overdue','Next 7 days','Next 30 days'])
    selected_date=c3.date_input('📅 Schedule Date',value=TODAY,help='Calendar icon पर click करके date चुनें। उस date की scheduled machines नीचे दिखाई देंगी।')
    search=c4.text_input('Machine / Code search')
    x=PLAN.merge(MACH[['machine_code','location','make_model']],on='machine_code',how='left')
    if loc!='ALL': x=x[x.location==loc]
    if days=='Selected date': x=x[x.scheduled_date==selected_date]
    elif days=='Due/Overdue': x=x[x.scheduled_date<=TODAY]
    elif days=='Next 7 days': x=x[(x.scheduled_date>=TODAY)&(x.scheduled_date<=TODAY+timedelta(days=7))]
    elif days=='Next 30 days': x=x[(x.scheduled_date>=TODAY)&(x.scheduled_date<=TODAY+timedelta(days=30))]
    if search: x=x[x.machine_name.str.contains(search,case=False)|x.machine_code.str.contains(search,case=False)]
    x=x.sort_values(['scheduled_date','machine_name'])
    if days=='Selected date':
        st.info(f'📅 {selected_date:%d-%m-%Y} को {len(x)} machine(s) की PM scheduled है।')
        if len(x):
            scheduled_options=[f"{r.machine_name} | {r.machine_code}" for _,r in x.iterrows()]
            selected_machine=st.selectbox('Select machine scheduled on this date',scheduled_options,key='pm_plan_machine_pick')
            selected_code=selected_machine.split(' | ')[-1]
            st.session_state['pmcode']=selected_code
            sm=machine_row(selected_code)
            st.success(f'Selected: {sm.machine_name} · {selected_code} · {sm.location}. PM Check Sheet tab में यही machine pre-selected रहेगी।')
        else:
            st.warning('इस selected date पर कोई PM activity scheduled नहीं है। दूसरी date चुनें।')
    st.dataframe(x,use_container_width=True,hide_index=True,column_config={'scheduled_date':st.column_config.DateColumn('Scheduled Date',format='DD-MM-YYYY')})
    st.caption('Calendar से date चुनें → उस date की machines filter होंगी → machine select करें → PM Check Sheet tab में वही machine automatically pre-selected होगी।')

with T[2]:
    st.subheader('Preventive Maintenance Check Sheet'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode'); mr=machine_row(code); st.info(f"{mr.machine_name} | {mr.location} | {mr.make_model}"); sheet=checklist_for(code)
    if not sheet or sheet not in CHECKS: st.warning('⚠️ PM Checklist Pending / Not Configured for this machine. Use Checklist Mapping tab when checklist becomes available.')
    else:
        st.caption(f'Checklist source: {sheet} · Machine code auto-linked: {code}'); jid=st.text_input('PM Work Order / Job ID',value=new_id('PM'),key='pmjid'); results=[]
        with st.form('pmform'):
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c=st.columns([5,2,4]); a.write(f'{i}. {pt}'); status=b.selectbox('Status',['OK','NOT OK','N/A'],key=f's{i}',label_visibility='collapsed'); remark=c.text_input('Action / Remark',key=f'r{i}',label_visibility='collapsed'); results.append((pt,status,remark))
            hot=st.checkbox('Hot work involved'); height=st.checkbox('Height work involved'); submit=st.form_submit_button('Submit PM & Update History',type='primary')
        if submit:
            now=datetime.now().isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'PM',code,mr.machine_name,mr.location,now,'Scheduled preventive maintenance','OPEN',int(hot),int(height),None))
            for pt,status,remark in results:execsql('insert into pm_checks(job_id,machine_code,check_point,result,action,remark,created_at) values(?,?,?,?,?,?,?)',(jid,code,pt,status,remark,remark,now))
            issues=[f'{p}: {r}' for p,s,r in results if s=='NOT OK']; action='; '.join(issues) if issues else 'PM checklist completed; no abnormality recorded.'; execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,'PM',now,'Scheduled PM',action,now,'Checklist submitted'))
            if hot:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,'PM related hot work','DRAFT'))
            if height:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,'PM related height work','DRAFT'))
            st.success(f'PM saved. History updated. Job ID: {jid}. Required permit drafts created automatically.')

with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f"{mr.machine_name} | {mr.location} | {mr.make_model}")
    with st.form('bmstart'):
        problem=st.text_area('Breakdown / Problem Details'); cause=st.text_input('Immediate suspected cause (if known)'); spares=st.text_input('Spares / material used or expected'); hot=st.checkbox('Hot work required'); height=st.checkbox('Height work required'); downtime=st.number_input('Downtime hours',min_value=0.0,step=0.25); action=st.text_area('Action Taken / Planned'); submit=st.form_submit_button('Create BM Work Order & Linked Records',type='primary')
    if submit:
        jid=new_id('BM'); now=datetime.now().isoformat(timespec='minutes'); execsql('insert into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'BM',code,mr.machine_name,mr.location,now,problem,'OPEN',int(hot),int(height),None)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,remark) values(?,?,?,?,?,?,?)',(jid,code,'BM',now,problem,action,'BM open')); execsql('insert into breakdowns(job_id,machine_code,failure,cause,downtime_hr,spares,action,status) values(?,?,?,?,?,?,?,?)',(jid,code,problem,cause,downtime,spares,action,'OPEN')); execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,now,problem,cause,action,spares,downtime,'OPEN','')); execsql('insert into whywhy(job_id,machine_code,problem,status) values(?,?,?,?)',(jid,code,problem,'DRAFT'))
        if hot:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,problem,'DRAFT'))
        if height:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,problem,'DRAFT'))
        st.success(f'{jid} created → Machine History + Breakdown History + Why-Why draft + applicable Permit draft(s) linked automatically.')

with T[4]:
    st.subheader('Machine History Card — PM/BM'); code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}'); activity_type=st.radio('Maintenance Activity Type',['PM','BM'],horizontal=True,key='hist_activity_type'); st.caption('Select PM for Preventive Maintenance or BM for Breakdown Maintenance. You can add a new history entry below.'); st.markdown('### ➕ Fill / Add Maintenance History'); default_jid=new_id(activity_type)
    with st.form('manual_history_form',clear_on_submit=True):
        c1,c2,c3=st.columns([1.4,1,1]); jid=c1.text_input('Job / Work Order ID',value=default_jid); start_date=c2.date_input('Start Date',value=TODAY); start_time=c3.time_input('Start Time',value=datetime.now().time().replace(second=0,microsecond=0)); problem=st.text_area('Problem / Maintenance Activity',placeholder='PM activity performed or breakdown/problem details'); action=st.text_area('Action Taken / Work Done',placeholder='Inspection, repair, replacement, adjustment, lubrication, etc.'); r1,r2=st.columns(2); restart_date=r1.date_input('Restart / Completion Date',value=TODAY); restart_time=r2.time_input('Restart / Completion Time',value=datetime.now().time().replace(second=0,microsecond=0)); remark=st.text_area('Remark / Observation')
        if activity_type=='BM': b1,b2=st.columns(2); cause=b1.text_input('Breakdown Cause / Suspected Cause'); downtime=b2.number_input('Downtime Hours',min_value=0.0,step=0.25); spares=st.text_input('Spares / Material Used')
        else:cause=''; downtime=0.0; spares=''
        save_history=st.form_submit_button(f'Save {activity_type} History',type='primary')
    if save_history:
        if not problem.strip():st.error('Problem / Maintenance Activity field is required.')
        elif not action.strip():st.error('Action Taken / Work Done field is required.')
        else:
            start_dt=datetime.combine(start_date,start_time).isoformat(timespec='minutes'); restart_dt=datetime.combine(restart_date,restart_time).isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,activity_type,code,mr.machine_name,mr.location,start_dt,problem,'CLOSED',0,0,restart_dt)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,activity_type,start_dt,problem,action,restart_dt,remark))
            if activity_type=='BM':
                execsql('insert into breakdowns(job_id,machine_code,failure,cause,downtime_hr,spares,action,status) values(?,?,?,?,?,?,?,?)',(jid,code,problem,cause,downtime,spares,action,'CLOSED')); execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,start_dt,problem,cause,action,spares,downtime,'CLOSED',remark)); existing=q('select id from whywhy where job_id=?',(jid,));
                if not len(existing):execsql('insert into whywhy(job_id,machine_code,problem,status) values(?,?,?,?)',(jid,code,problem,'DRAFT'))
                st.success(f'BM history saved for {mr.machine_name}. Breakdown History and Why-Why draft also linked automatically. Job ID: {jid}')
            else:st.success(f'PM history saved for {mr.machine_name}. Job ID: {jid}')
    st.markdown('### 📚 Saved History'); history_view=q('select job_id,maintenance_type,start_dt,problem,action_taken,restart_dt,remark from history where machine_code=? and maintenance_type=? order by id desc',(code,activity_type)); st.dataframe(history_view,use_container_width=True,hide_index=True)

with T[5]:
    st.subheader('Breakdown History Card — Editable Activity Log')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
    st.caption('हर breakdown/maintenance activity को अलग row में दर्ज करें। नीचे + row से जितनी चाहें entries जोड़ सकते हैं।')
    existing=q('select id,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark from breakdown_activity_log where machine_code=? order by id',(code,))
    if len(existing)==0:
        existing=pd.DataFrame([{ 'id':None,'job_id':new_id('BM'),'activity_dt':datetime.now().isoformat(timespec='minutes'),'failure':'','cause':'','action':'','spares':'','downtime_hr':0.0,'status':'OPEN','remark':'' }])
    edited=st.data_editor(existing,num_rows='dynamic',use_container_width=True,hide_index=True,key=f'bd_editor_{code}',column_config={
        'id':st.column_config.NumberColumn('ID',disabled=True),'job_id':st.column_config.TextColumn('Job / WO ID'),'activity_dt':st.column_config.TextColumn('Date / Time'),'failure':st.column_config.TextColumn('Problem / Failure',width='large'),'cause':st.column_config.TextColumn('Cause',width='medium'),'action':st.column_config.TextColumn('Activity / Action Taken',width='large'),'spares':st.column_config.TextColumn('Spares / Material',width='medium'),'downtime_hr':st.column_config.NumberColumn('Downtime Hr',min_value=0.0,step=0.25),'status':st.column_config.SelectboxColumn('Status',options=['OPEN','IN PROGRESS','CLOSED']),'remark':st.column_config.TextColumn('Remark',width='large')})
    csave,cinfo=st.columns([1,3])
    if csave.button('💾 Save Breakdown History',type='primary',use_container_width=True):
        cleaned=edited.copy(); cleaned=cleaned[cleaned[['failure','action','cause','spares','remark']].fillna('').astype(str).apply(lambda r: ''.join(r).strip()!='',axis=1)]
        execsql('delete from breakdown_activity_log where machine_code=?',(code,))
        for _,r in cleaned.iterrows():
            jid=str(r.get('job_id') or new_id('BM')); adt=str(r.get('activity_dt') or datetime.now().isoformat(timespec='minutes')); failure=str(r.get('failure') or ''); cause=str(r.get('cause') or ''); action=str(r.get('action') or ''); spares=str(r.get('spares') or ''); downtime=float(r.get('downtime_hr') or 0.0); status=str(r.get('status') or 'OPEN'); remark=str(r.get('remark') or '')
            execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,adt,failure,cause,action,spares,downtime,status,remark))
        st.success(f'{len(cleaned)} breakdown activity row(s) saved for {mr.machine_name}.'); st.rerun()
    cinfo.info('नई row जोड़ने के लिए table के नीचे + icon/use dynamic row करें; पुरानी rows भी edit की जा सकती हैं।')

with T[6]:
    st.subheader('Work Orders & Safety Permits'); st.markdown('**Open / Recent Work Orders**'); st.dataframe(q('select * from jobs order by opened_at desc limit 100'),use_container_width=True,hide_index=True); st.markdown('**Height / Hot Work Permits**'); permits=q('select * from permits order by id desc'); st.dataframe(permits,use_container_width=True,hide_index=True)
    if len(permits):
        pid=st.selectbox('Edit permit',permits.permit_no.tolist()); r=permits[permits.permit_no==pid].iloc[0]
        with st.form('permitform'):
            sup=st.text_input('Supervisor',value=str(r.supervisor or '')); activity=st.text_input('Activity',value=str(r.activity or '')); start=st.text_input('Start date/time',value=str(r.start_dt or '')); end=st.text_input('End date/time',value=str(r.end_dt or '')); precautions=st.text_area('Additional precautions / concern noticed',value=str(r.precautions or '')); status=st.selectbox('Permit Status',['DRAFT','GRANTED','CLOSED'],index=['DRAFT','GRANTED','CLOSED'].index(r.status if r.status in ['DRAFT','GRANTED','CLOSED'] else 'DRAFT')); save=st.form_submit_button('Save Permit')
        if save:execsql('update permits set supervisor=?,activity=?,start_dt=?,end_dt=?,precautions=?,status=? where permit_no=?',(sup,activity,start,end,precautions,status,pid));st.success('Permit updated.')

with T[7]:
    st.subheader('Why-Why Analysis / Root Cause Analysis'); drafts=q('select * from whywhy order by id desc')
    if not len(drafts):st.info('A Why-Why draft is automatically created when a BM Work Order is opened.')
    else:
        jid=st.selectbox('BM Job ID',drafts.job_id.tolist()); r=drafts[drafts.job_id==jid].iloc[0]; mr=machine_row(r.machine_code); st.info(f'{mr.machine_name} | {r.machine_code} | Problem: {r.problem}')
        with st.form('whyform'):
            why1=st.text_area('Why 1?',value=str(r.why1 or '')); why2=st.text_area('Why 2?',value=str(r.why2 or '')); why3=st.text_area('Why 3?',value=str(r.why3 or '')); why4=st.text_area('Why 4?',value=str(r.why4 or '')); why5=st.text_area('Why 5?',value=str(r.why5 or '')); root=st.text_area('Root Cause',value=str(r.root_cause or '')); corr=st.text_area('Corrective Action',value=str(r.corrective or '')); prev=st.text_area('Preventive Action',value=str(r.preventive or '')); owner=st.text_input('Responsible Person',value=str(r.owner or '')); target=st.date_input('Target Date',value=TODAY); eff=st.text_area('Effectiveness Check',value=str(r.effectiveness or '')); status=st.selectbox('RCA Status',['DRAFT','ACTION OPEN','CLOSED']); save=st.form_submit_button('Save Why-Why Analysis',type='primary')
        if save:execsql('update whywhy set why1=?,why2=?,why3=?,why4=?,why5=?,root_cause=?,corrective=?,preventive=?,owner=?,target_date=?,effectiveness=?,status=? where job_id=?',(why1,why2,why3,why4,why5,root,corr,prev,owner,str(target),eff,status,jid));st.success('Why-Why analysis saved and linked to BM job.')

with T[8]: st.subheader('Machine / Equipment Master'); st.dataframe(MACH,use_container_width=True,hide_index=True); st.caption('Machine Code is the primary link across PM, BM, History, Permit and Why-Why records.')
with T[9]:
    st.subheader('Machine → PM Checklist Mapping'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='mapcode'); mr=machine_row(code); current=checklist_for(code); opts=['NOT CONFIGURED']+list(CHECKS.keys()); idx=opts.index(current) if current in opts else 0; sel=st.selectbox('Checklist Template',opts,index=idx)
    if st.button('Save Mapping',type='primary'):
        if sel=='NOT CONFIGURED':execsql('delete from checklist_map where machine_code=?',(code,))
        else:execsql('insert or replace into checklist_map(machine_code,sheet_name) values(?,?)',(code,sel))
        st.success(f'Mapping saved: {mr.machine_name} → {sel}')
    st.caption('Missing machine checklists can be added later without rebuilding the dashboard. Map them here when available.')