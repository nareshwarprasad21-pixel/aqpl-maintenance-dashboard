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
[data-testid="stDataFrame"]{border:1px solid #263958;border-radius:12px;overflow:hidden}.flow{padding:12px 15px;border-radius:12px;background:#101f35;border:1px solid #263958;margin:7px 0}
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
    n=name.lower(); rules=[
      ('jaw','Jaw crusher'),('secondary cone','sec cone cr'),('tertiary cone','Tertiary cone crusher'),('primary class','Vibro acreen'),('scrubber','scrubber'),('washing class','washing screen'),('de-water','DEWAT.SCREEN'),
      ('heater-1','Heter-1'),('heater-2','Heter-2'),('heater-3','Heter-3'),('primary ball','P.B.MILL'),('secondary ball','S.B.mill'),('primary dynamic','P.Dy.seperator'),('secondary dynamic','S.dy.seprator'),('primary bag','P.baghouse'),('secondary bag','s.baghouse'),('primary vibro','P.vibroscreen'),('secondary vibro','S.vibro screen'),('magnetic','magnetic sep.-1'),('eot crane-1','EOT CRANE-1'),('eot crane-2','EOT CRANE-2'),('eot crane-3','EOT CRAN-3'),('compressor-1','compressor-1'),('compressor-2','compressor-2'),('compressor-3','compressor-3'),('compressor-4','compressor-4'),('chiller-1','chiller-1'),('chiller-2','chiller-2'),('chiller-3','chiller-3')]
    for k,s in rules:
        if k in n:return s
    return ''
def checklist_for(code):
    r=q('select sheet_name from checklist_map where machine_code=?',(code,))
    if len(r) and r.iloc[0,0] in CHECKS:return r.iloc[0,0]
    name=machine_row(code).machine_name
    return suggest_sheet(name)

def top_header():
    st.markdown('<div class="hero"><h1>🛠️ ASIAN QUARTZ PVT LTD — Maintenance Management Dashboard</h1><div class="sub">PM • Breakdown • Machine History • Work Orders • Height/Hot Work Permits • Why-Why RCA</div></div>',unsafe_allow_html=True)
top_header()

TODAY=date.today(); window=TODAY+timedelta(days=7)
due=PLAN[PLAN.scheduled_date==TODAY]; overdue=PLAN[PLAN.scheduled_date<TODAY]
hist=q('select * from history'); jobs=q('select * from jobs')
open_bm=jobs[(jobs.job_type=='BM') & (jobs.status!='CLOSED')] if len(jobs) else jobs
open_per=q("select * from permits where status!='CLOSED'")
upcoming=PLAN[(PLAN.scheduled_date>TODAY)&(PLAN.scheduled_date<=window)]
cols=st.columns(5)
for col,title,val,cls in zip(cols,['PM Due Today','PM Next 7 Days','Open Breakdowns','Open Permits','Machine Master'],[len(due),len(upcoming),len(open_bm),len(open_per),len(MACH)],['yellow','purple','red','yellow','green']):
    col.markdown(f'<div class="kpi {cls}"><span class="sub">{title}</span><br><b>{val}</b></div>',unsafe_allow_html=True)

T=st.tabs(['🏠 Dashboard','📅 PM Plan','✅ PM Check Sheet','🚨 Breakdown','🗂️ Machine History','📋 Breakdown History','🧾 Work Orders & Permits','🔎 Why-Why Analysis','⚙️ Equipment Master','🔗 Checklist Mapping'])

with T[0]:
    st.subheader('Today / Upcoming Maintenance')
    if len(due): st.warning(f'{len(due)} preventive maintenance activities are due today.')
    else: st.success('No PM activity is scheduled exactly for today.')
    st.dataframe(pd.concat([due.assign(Status='DUE TODAY'),upcoming.assign(Status='UPCOMING')]).head(30),use_container_width=True,hide_index=True)
    st.subheader('Linked Workflow')
    st.markdown('<div class="flow"><b>PM:</b> PM Plan → Due Alert → Machine Code → PM Check Sheet → Machine History → Close Job / Next Due</div>',unsafe_allow_html=True)
    st.markdown('<div class="flow"><b>BM:</b> Breakdown → Work Order → Machine History → Breakdown History → Permit(s) if needed → Why-Why RCA → Closure</div>',unsafe_allow_html=True)

with T[1]:
    st.subheader('Preventive Maintenance Plan — 2026–27')
    c1,c2,c3=st.columns(3); loc=c1.selectbox('Location',['ALL']+sorted(MACH.location.unique().tolist())); days=c2.selectbox('Window',['All','Due/Overdue','Next 7 days','Next 30 days']); search=c3.text_input('Machine / Code search')
    x=PLAN.merge(MACH[['machine_code','location','make_model']],on='machine_code',how='left')
    if loc!='ALL':x=x[x.location==loc]
    if days=='Due/Overdue':x=x[x.scheduled_date<=TODAY]
    elif days=='Next 7 days':x=x[(x.scheduled_date>=TODAY)&(x.scheduled_date<=TODAY+timedelta(days=7))]
    elif days=='Next 30 days':x=x[(x.scheduled_date>=TODAY)&(x.scheduled_date<=TODAY+timedelta(days=30))]
    if search:x=x[x.machine_name.str.contains(search,case=False)|x.machine_code.str.contains(search,case=False)]
    x=x.sort_values('scheduled_date'); st.dataframe(x,use_container_width=True,hide_index=True)
    st.caption('PM date reaches today → dashboard Due alert. Open PM Check Sheet tab and select the same Machine Code.')

with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode'); mr=machine_row(code); st.info(f"{mr.machine_name} | {mr.location} | {mr.make_model}")
    sheet=checklist_for(code)
    if not sheet or sheet not in CHECKS:
        st.warning('⚠️ PM Checklist Pending / Not Configured for this machine. Use Checklist Mapping tab when checklist becomes available.')
    else:
        st.caption(f'Checklist source: {sheet} · Machine code auto-linked: {code}')
        jid=st.text_input('PM Work Order / Job ID',value=new_id('PM'),key='pmjid')
        results=[]
        with st.form('pmform'):
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c=st.columns([5,2,4]); a.write(f'{i}. {pt}'); status=b.selectbox('Status',['OK','NOT OK','N/A'],key=f's{i}',label_visibility='collapsed'); remark=c.text_input('Action / Remark',key=f'r{i}',label_visibility='collapsed'); results.append((pt,status,remark))
            hot=st.checkbox('Hot work involved'); height=st.checkbox('Height work involved'); submit=st.form_submit_button('Submit PM & Update History',type='primary')
        if submit:
            now=datetime.now().isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'PM',code,mr.machine_name,mr.location,now,'Scheduled preventive maintenance','OPEN',int(hot),int(height),None))
            for pt,status,remark in results: execsql('insert into pm_checks(job_id,machine_code,check_point,result,action,remark,created_at) values(?,?,?,?,?,?,?)',(jid,code,pt,status,remark,remark,now))
            issues=[f'{p}: {r}' for p,s,r in results if s=='NOT OK']; action='; '.join(issues) if issues else 'PM checklist completed; no abnormality recorded.'
            execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,'PM',now,'Scheduled PM',action,now,'Checklist submitted'))
            if hot: execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,'PM related hot work','DRAFT'))
            if height: execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,'PM related height work','DRAFT'))
            st.success(f'PM saved. History updated. Job ID: {jid}. Required permit drafts created automatically.')

with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f"{mr.machine_name} | {mr.location} | {mr.make_model}")
    with st.form('bmstart'):
        problem=st.text_area('Breakdown / Problem Details'); cause=st.text_input('Immediate suspected cause (if known)'); spares=st.text_input('Spares / material used or expected'); hot=st.checkbox('Hot work required'); height=st.checkbox('Height work required'); downtime=st.number_input('Downtime hours',min_value=0.0,step=0.25); action=st.text_area('Action Taken / Planned'); submit=st.form_submit_button('Create BM Work Order & Linked Records',type='primary')
    if submit:
        jid=new_id('BM'); now=datetime.now().isoformat(timespec='minutes'); execsql('insert into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'BM',code,mr.machine_name,mr.location,now,problem,'OPEN',int(hot),int(height),None)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,remark) values(?,?,?,?,?,?,?)',(jid,code,'BM',now,problem,action,'BM open')); execsql('insert into breakdowns(job_id,machine_code,failure,cause,downtime_hr,spares,action,status) values(?,?,?,?,?,?,?,?)',(jid,code,problem,cause,downtime,spares,action,'OPEN')); execsql('insert into whywhy(job_id,machine_code,problem,status) values(?,?,?,?)',(jid,code,problem,'DRAFT'))
        if hot:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,problem,'DRAFT'))
        if height:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,problem,'DRAFT'))
        st.success(f'{jid} created → Machine History + Breakdown History + Why-Why draft + applicable Permit draft(s) linked automatically.')

with T[4]:
    st.subheader('Machine History Card — PM + BM')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='histcode'); mr=machine_row(code); st.write(f'**{mr.machine_name}** · {code} · {mr.location} · {mr.make_model}')
    st.dataframe(q('select job_id,maintenance_type,start_dt,problem,action_taken,restart_dt,remark from history where machine_code=? order by id desc',(code,)),use_container_width=True,hide_index=True)

with T[5]:
    st.subheader('Breakdown History Card')
    code=st.selectbox('Machine',MACH.machine_code.tolist(),key='bdhcode'); st.dataframe(q('select * from breakdowns where machine_code=? order by id desc',(code,)),use_container_width=True,hide_index=True)

with T[6]:
    st.subheader('Work Orders & Safety Permits')
    st.markdown('**Open / Recent Work Orders**'); st.dataframe(q('select * from jobs order by opened_at desc limit 100'),use_container_width=True,hide_index=True)
    st.markdown('**Height / Hot Work Permits**')
    permits=q('select * from permits order by id desc')
    st.dataframe(permits,use_container_width=True,hide_index=True)
    if len(permits):
        pid=st.selectbox('Edit permit',permits.permit_no.tolist()); r=permits[permits.permit_no==pid].iloc[0]
        with st.form('permitform'):
            sup=st.text_input('Supervisor',value=str(r.supervisor or '')); activity=st.text_input('Activity',value=str(r.activity or '')); start=st.text_input('Start date/time',value=str(r.start_dt or '')); end=st.text_input('End date/time',value=str(r.end_dt or '')); precautions=st.text_area('Additional precautions / concern noticed',value=str(r.precautions or '')); status=st.selectbox('Permit Status',['DRAFT','GRANTED','CLOSED'],index=['DRAFT','GRANTED','CLOSED'].index(r.status if r.status in ['DRAFT','GRANTED','CLOSED'] else 'DRAFT')); save=st.form_submit_button('Save Permit')
        if save:execsql('update permits set supervisor=?,activity=?,start_dt=?,end_dt=?,precautions=?,status=? where permit_no=?',(sup,activity,start,end,precautions,status,pid));st.success('Permit updated.')

with T[7]:
    st.subheader('Why-Why Analysis / Root Cause Analysis')
    drafts=q('select * from whywhy order by id desc')
    if not len(drafts):st.info('A Why-Why draft is automatically created when a BM Work Order is opened.')
    else:
        jid=st.selectbox('BM Job ID',drafts.job_id.tolist()); r=drafts[drafts.job_id==jid].iloc[0]; mr=machine_row(r.machine_code); st.info(f'{mr.machine_name} | {r.machine_code} | Problem: {r.problem}')
        with st.form('whyform'):
            why1=st.text_area('Why 1?',value=str(r.why1 or '')); why2=st.text_area('Why 2?',value=str(r.why2 or '')); why3=st.text_area('Why 3?',value=str(r.why3 or '')); why4=st.text_area('Why 4?',value=str(r.why4 or '')); why5=st.text_area('Why 5?',value=str(r.why5 or '')); root=st.text_area('Root Cause',value=str(r.root_cause or '')); corr=st.text_area('Corrective Action',value=str(r.corrective or '')); prev=st.text_area('Preventive Action',value=str(r.preventive or '')); owner=st.text_input('Responsible Person',value=str(r.owner or '')); target=st.date_input('Target Date',value=TODAY); eff=st.text_area('Effectiveness Check',value=str(r.effectiveness or '')); status=st.selectbox('RCA Status',['DRAFT','ACTION OPEN','CLOSED']); save=st.form_submit_button('Save Why-Why Analysis',type='primary')
        if save:execsql('update whywhy set why1=?,why2=?,why3=?,why4=?,why5=?,root_cause=?,corrective=?,preventive=?,owner=?,target_date=?,effectiveness=?,status=? where job_id=?',(why1,why2,why3,why4,why5,root,corr,prev,owner,str(target),eff,status,jid));st.success('Why-Why analysis saved and linked to BM job.')

with T[8]:
    st.subheader('Machine / Equipment Master')
    st.dataframe(MACH,use_container_width=True,hide_index=True); st.caption('Machine Code is the primary link across PM, BM, History, Permit and Why-Why records.')

with T[9]:
    st.subheader('Machine → PM Checklist Mapping')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='mapcode'); mr=machine_row(code); current=checklist_for(code); opts=['NOT CONFIGURED']+list(CHECKS.keys()); idx=opts.index(current) if current in opts else 0; sel=st.selectbox('Checklist Template',opts,index=idx)
    if st.button('Save Mapping',type='primary'):
        if sel=='NOT CONFIGURED':execsql('delete from checklist_map where machine_code=?',(code,))
        else:execsql('insert or replace into checklist_map(machine_code,sheet_name) values(?,?)',(code,sel))
        st.success(f'Mapping saved: {mr.machine_name} → {sel}')
    st.caption('Missing machine checklists can be added later without rebuilding the dashboard. Map them here when available.')