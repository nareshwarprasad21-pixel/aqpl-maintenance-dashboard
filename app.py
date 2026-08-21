import streamlit as st
import pandas as pd
import sqlite3, json, os, re
from typing import Any
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

try:
    from supabase import create_client
except ImportError:
    create_client=None
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

TABLE_COLUMNS={
    'jobs':['job_id','job_type','machine_code','machine_name','location','opened_at','problem','status','hot_work','height_work','closed_at'],
    'pm_checks':['id','job_id','machine_code','check_point','result','action','remark','created_at'],
    'history':['id','job_id','machine_code','maintenance_type','start_dt','problem','action_taken','restart_dt','remark'],
    'breakdowns':['id','job_id','machine_code','failure','cause','downtime_hr','spares','action','status'],
    'breakdown_activity_log':['id','machine_code','job_id','activity_dt','failure','cause','action','spares','downtime_hr','status','remark'],
    'permits':['id','permit_no','job_id','permit_type','machine_code','activity','supervisor','start_dt','end_dt','status','precautions'],
    'whywhy':['id','job_id','machine_code','problem','why1','why2','why3','why4','why5','root_cause','corrective','preventive','owner','target_date','effectiveness','status'],
    'checklist_map':['machine_code','sheet_name']
}

def _secret(name):
    try:
        return str(st.secrets.get(name,'')).strip()
    except Exception:
        return str(os.getenv(name,'')).strip()

SUPABASE_URL=_secret('SUPABASE_URL')
SUPABASE_SECRET_KEY=_secret('SUPABASE_SECRET_KEY') or _secret('SUPABASE_SERVICE_ROLE_KEY')
USE_SUPABASE=bool(create_client and SUPABASE_URL and SUPABASE_SECRET_KEY)
SB=create_client(SUPABASE_URL,SUPABASE_SECRET_KEY) if USE_SUPABASE else None

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

def _value_or(value:Any,default):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError,ValueError):
        pass
    return default if str(value).strip()=='' else value

def _clean_value(value:Any):
    if value is None or (isinstance(value,float) and pd.isna(value)):
        return None
    if isinstance(value,(pd.Timestamp,datetime,date)):
        return value.isoformat()
    return value

def _parse_where(builder,where_part,args):
    arg_index=0
    for clause in re.split(r'\s+and\s+',where_part,flags=re.I):
        clause=clause.strip()
        match=re.match(r"(\w+)\s*(=|!=|<>)\s*(\?|'.*?'|\".*?\"|[-\d.]+)$",clause)
        if not match:
            raise ValueError(f'Unsupported database filter: {clause}')
        column,operator,token=match.groups()
        if token=='?':
            value=args[arg_index]; arg_index+=1
        elif token[:1] in ("'",'"'):
            value=token[1:-1]
        else:
            value=float(token) if '.' in token else int(token)
        builder=builder.neq(column,value) if operator in ('!=','<>') else builder.eq(column,value)
    return builder

def q(sql,args=()):
    if not USE_SUPABASE:
        return pd.read_sql_query(sql,C,params=args)
    normalized=' '.join(sql.strip().split())
    match=re.match(r'select (.+?) from (\w+)(.*)$',normalized,re.I)
    if not match:
        raise ValueError(f'Unsupported SELECT: {sql}')
    selected,table,tail=match.groups()
    limit_match=re.search(r'\s+limit\s+(\d+)\s*$',tail,re.I)
    limit=int(limit_match.group(1)) if limit_match else None
    if limit_match: tail=tail[:limit_match.start()]
    order_match=re.search(r'\s+order\s+by\s+(\w+)(?:\s+(asc|desc))?\s*$',tail,re.I)
    order_col=order_match.group(1) if order_match else None
    order_desc=bool(order_match and (order_match.group(2) or '').lower()=='desc')
    if order_match: tail=tail[:order_match.start()]
    where_match=re.search(r'\s+where\s+(.+)$',tail,re.I)
    builder=SB.table(table).select(selected)
    if where_match: builder=_parse_where(builder,where_match.group(1),args)
    if order_col: builder=builder.order(order_col,desc=order_desc)
    if limit is not None: builder=builder.limit(limit)
    rows=builder.execute().data or []
    columns=TABLE_COLUMNS[table] if selected=='*' else [x.strip() for x in selected.split(',')]
    return pd.DataFrame(rows,columns=columns)

def execsql(sql,args=()):
    if not USE_SUPABASE:
        C.execute(sql,args); C.commit(); return
    normalized=' '.join(sql.strip().split())
    insert_match=re.match(r'insert\s+(or\s+replace\s+)?into\s+(\w+)\s*(?:\(([^)]+)\))?\s+values\s*\(([^)]+)\)',normalized,re.I)
    if insert_match:
        replace,table,columns,_=insert_match.groups()
        cols=[c.strip() for c in columns.split(',')] if columns else TABLE_COLUMNS[table]
        payload={col:_clean_value(value) for col,value in zip(cols,args)}
        if payload.get('id') is None: payload.pop('id',None)
        command=SB.table(table).upsert(payload) if replace else SB.table(table).insert(payload)
        command.execute(); return
    update_match=re.match(r'update\s+(\w+)\s+set\s+(.+?)\s+where\s+(\w+)\s*=\s*\?',normalized,re.I)
    if update_match:
        table,set_part,where_col=update_match.groups()
        set_cols=[piece.split('=')[0].strip() for piece in set_part.split(',')]
        payload={col:_clean_value(value) for col,value in zip(set_cols,args[:-1])}
        SB.table(table).update(payload).eq(where_col,args[-1]).execute(); return
    delete_match=re.match(r'delete\s+from\s+(\w+)\s+where\s+(\w+)\s*=\s*\?',normalized,re.I)
    if delete_match:
        table,where_col=delete_match.groups()
        SB.table(table).delete().eq(where_col,args[0]).execute(); return
    raise ValueError(f'Unsupported database write: {sql}')

def _bootstrap_local_data():
    if not USE_SUPABASE or not os.path.exists(DB):
        return
    marker='supabase_bootstrap_complete'
    if st.session_state.get(marker):
        return
    for table,columns in TABLE_COLUMNS.items():
        remote=SB.table(table).select(columns[0]).limit(1).execute().data or []
        if remote:
            continue
        try:
            local=pd.read_sql_query(f'select * from {table}',C)
        except Exception:
            continue
        if local.empty:
            continue
        records=[{k:_clean_value(v) for k,v in row.items()} for row in local.to_dict('records')]
        SB.table(table).insert(records).execute()
    st.session_state[marker]=True

if USE_SUPABASE:
    try:
        _bootstrap_local_data()
        st.sidebar.success('☁️ Supabase connected')
    except Exception as exc:
        st.sidebar.error(f'Supabase connection error: {exc}')
else:
    st.sidebar.warning('Local database active · add Supabase secrets')

def build_pm_checksheet_pdf(job,checks,machine):
    """Return a professional A4 PM checklist as PDF bytes."""
    def val(source,key,default=''):
        try:
            value=source.get(key,default)
        except AttributeError:
            value=default
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except (TypeError,ValueError):
            pass
        return str(value)

    regular='Helvetica'; bold='Helvetica-Bold'
    font_paths=[
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/dejavu/DejaVuSans.ttf','/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf')
    ]
    for regular_path,bold_path in font_paths:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont('AQPLSans',regular_path))
                pdfmetrics.registerFont(TTFont('AQPLSansBold',bold_path))
                regular='AQPLSans'; bold='AQPLSansBold'
                break
            except Exception:
                pass

    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,
                          topMargin=15*mm,bottomMargin=16*mm,
                          title=f"PM Check Sheet - {val(job,'job_id')}",
                          author='Asian Quartz Pvt Ltd')
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle('AQPLTitle',parent=styles['Title'],fontName=bold,
        fontSize=15,leading=18,textColor=colors.HexColor('#10213b'),alignment=TA_CENTER,spaceAfter=2*mm)
    subtitle_style=ParagraphStyle('AQPLSubTitle',parent=styles['Heading2'],fontName=bold,
        fontSize=11,leading=14,textColor=colors.HexColor('#1d4ed8'),alignment=TA_CENTER,spaceAfter=4*mm)
    body_style=ParagraphStyle('AQPLBody',parent=styles['BodyText'],fontName=regular,
        fontSize=7.5,leading=9.5,textColor=colors.HexColor('#111827'))
    body_bold=ParagraphStyle('AQPLBodyBold',parent=body_style,fontName=bold)
    header_style=ParagraphStyle('AQPLHeader',parent=body_bold,textColor=colors.white,alignment=TA_CENTER)
    small_style=ParagraphStyle('AQPLSmall',parent=body_style,fontSize=7,leading=8.5)
    story=[
        Paragraph('ASIAN QUARTZ PVT LTD',title_style),
        Paragraph('PREVENTIVE MAINTENANCE CHECK SHEET',subtitle_style)
    ]
    meta=[
        [Paragraph('<b>Machine Name</b>',body_bold),Paragraph(escape(val(machine,'machine_name')),body_style),
         Paragraph('<b>Machine Code</b>',body_bold),Paragraph(escape(val(machine,'machine_code')),body_style)],
        [Paragraph('<b>Location / Type</b>',body_bold),Paragraph(escape(val(machine,'location')),body_style),
         Paragraph('<b>Make / Model</b>',body_bold),Paragraph(escape(val(machine,'make_model')),body_style)],
        [Paragraph('<b>Job / WO ID</b>',body_bold),Paragraph(escape(val(job,'job_id')),body_style),
         Paragraph('<b>Maintenance Date</b>',body_bold),Paragraph(escape(val(job,'opened_at')),body_style)],
        [Paragraph('<b>Job Status</b>',body_bold),Paragraph(escape(val(job,'status','OPEN')),body_style),
         Paragraph('<b>Permit Requirement</b>',body_bold),
         Paragraph(f"Hot Work: {'YES' if val(job,'hot_work','0') in ('1','True','true') else 'NO'} &nbsp;&nbsp; Height Work: {'YES' if val(job,'height_work','0') in ('1','True','true') else 'NO'}",body_style)]
    ]
    meta_table=Table(meta,colWidths=[30*mm,61*mm,32*mm,61*mm])
    meta_table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.45,colors.HexColor('#94a3b8')),
        ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e2e8f0')),
        ('BACKGROUND',(2,0),(2,-1),colors.HexColor('#e2e8f0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)
    ]))
    story.extend([meta_table,Spacer(1,5*mm)])

    header=[Paragraph('<b>S.No.</b>',header_style),Paragraph('<b>Check Point</b>',header_style),
            Paragraph('<b>Status</b>',header_style),Paragraph('<b>Action Taken</b>',header_style),
            Paragraph('<b>Remarks / Observation</b>',header_style)]
    rows=[header]
    if isinstance(checks,pd.DataFrame):
        records=checks.to_dict('records')
    else:
        records=list(checks)
    for index,item in enumerate(records,1):
        rows.append([
            Paragraph(str(index),small_style),
            Paragraph(escape(val(item,'check_point')),small_style),
            Paragraph(escape(val(item,'result')),small_style),
            Paragraph(escape(val(item,'action')),small_style),
            Paragraph(escape(val(item,'remark')),small_style)
        ])
    checklist=Table(rows,colWidths=[12*mm,71*mm,22*mm,38*mm,41*mm],repeatRows=1)
    checklist.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#10213b')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#94a3b8')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ALIGN',(0,0),(0,-1),'CENTER'),('ALIGN',(2,1),(2,-1),'CENTER'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
        ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',(0,0),(-1,-1),3.5),('BOTTOMPADDING',(0,0),(-1,-1),3.5)
    ]))
    story.extend([checklist,Spacer(1,7*mm)])
    signatures=[
        [Paragraph('<b>Prepared / Performed By</b>',body_bold),
         Paragraph('<b>Checked By</b>',body_bold),
         Paragraph('<b>Approved By</b>',body_bold)],
        [Paragraph('<br/><br/>Name &amp; Sign: __________________',body_style),
         Paragraph('<br/><br/>Maintenance Engineer: ____________',body_style),
         Paragraph('<br/><br/>HOD / Plant Head: ________________',body_style)],
        [Paragraph('Date: _____________________________',body_style),
         Paragraph('Date: _____________________________',body_style),
         Paragraph('Date: _____________________________',body_style)]
    ]
    sign_table=Table(signatures,colWidths=[61.3*mm]*3)
    sign_table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#64748b')),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story.append(sign_table)

    def footer(canvas,document):
        canvas.saveState()
        canvas.setFont(regular,7)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(12*mm,8*mm,f"Document: AQPL/MAINT/PM | Job: {val(job,'job_id')}")
        canvas.drawRightString(A4[0]-12*mm,8*mm,f"Page {document.page}")
        canvas.restoreState()

    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()

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
    plan_start=min(PLAN.scheduled_date)
    plan_end=max(PLAN.scheduled_date)
    if 'pm_schedule_date' not in st.session_state:
        st.session_state['pm_schedule_date']=TODAY
    selected_date=c3.date_input(
        '📅 Schedule Date',
        min_value=plan_start,
        max_value=plan_end,
        key='pm_schedule_date',
        help='Calendar icon पर click करके past या future schedule date चुनें।'
    )
    # Keep the PM form on the same selected date so a back-dated checklist is
    # saved in history with the chosen maintenance date, not today's date.
    if st.session_state.get('pm_plan_last_synced_date') != selected_date:
        st.session_state['pm_maintenance_date']=selected_date
        st.session_state['pm_plan_last_synced_date']=selected_date
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
    st.caption(f'Available plan dates: {plan_start:%d-%m-%Y} से {plan_end:%d-%m-%Y}। Calendar से past date चुनें → machine select करें → PM Check Sheet tab में machine और Maintenance Date automatically set होंगे।')

with T[2]:
    st.subheader('Preventive Maintenance Check Sheet')
    code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='pmcode')
    mr=machine_row(code)
    sheet=checklist_for(code)
    if not sheet or sheet not in CHECKS:
        st.warning('⚠️ PM Checklist Pending / Not Configured for this machine. Use Checklist Mapping tab when checklist becomes available.')
    else:
        st.markdown(f'### PREVENTIVE MAINTENANCE CHECK SHEET FOR {mr.machine_name}')
        m1,m2,m3,m4=st.columns(4)
        m1.text_input('Machine Name',value=str(mr.machine_name),disabled=True,key='pm_machine_name')
        m2.text_input('Machine Number / Code',value=code,disabled=True,key='pm_machine_code')
        maintenance_date=m3.date_input('Maintenance Date',value=TODAY,key='pm_maintenance_date')
        machine_type=m4.text_input('Machine Type',value=str(mr.location),key='pm_machine_type')
        d1,d2=st.columns([2,1])
        d1.info(f'Make / Model: {mr.make_model} | Location: {mr.location} | Checklist source: {sheet}')
        jid=d2.text_input('PM Work Order / Job ID',value=new_id('PM'),key='pmjid')
        st.markdown('#### Checklist Details')
        st.caption('Actual AQPL format की तरह हर check point के लिए Status, Action और Remark अलग-अलग भरें।')
        results=[]
        with st.form('pmform'):
            h1,h2,h3,h4,h5=st.columns([0.7,4.6,2,3.4,3.4])
            h1.markdown('**S.No.**'); h2.markdown('**Check Points**'); h3.markdown('**Status**'); h4.markdown('**Actions**'); h5.markdown('**Remarks**')
            for i,pt in enumerate(CHECKS[sheet],1):
                a,b,c,d,e=st.columns([0.7,4.6,2,3.4,3.4])
                a.write(i)
                b.write(pt)
                status=c.selectbox('Status',['OK','NOT OK','N/A'],key=f's{i}',label_visibility='collapsed')
                action_txt=d.text_input('Action',key=f'a{i}',label_visibility='collapsed',placeholder='Work/action done')
                remark=e.text_input('Remark',key=f'r{i}',label_visibility='collapsed',placeholder='Observation/condition')
                results.append((pt,status,action_txt,remark))
            st.markdown('#### Safety / Permit Requirement')
            hot=st.checkbox('Hot work involved')
            height=st.checkbox('Height work involved')
            submit=st.form_submit_button('Submit PM Check Sheet & Update History',type='primary')
        if submit:
            now=datetime.combine(maintenance_date,datetime.now().time().replace(second=0,microsecond=0)).isoformat(timespec='minutes')
            execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'PM',code,mr.machine_name,mr.location,now,'Scheduled preventive maintenance','OPEN',int(hot),int(height),None))
            for pt,status,action_txt,remark in results:
                execsql('insert into pm_checks(job_id,machine_code,check_point,result,action,remark,created_at) values(?,?,?,?,?,?,?)',(jid,code,pt,status,action_txt,remark,now))
            issues=[]
            actions_done=[]
            for pt,status,action_txt,remark in results:
                if status=='NOT OK': issues.append(f'{pt}: {remark or "NOT OK"}')
                if action_txt.strip(): actions_done.append(f'{pt}: {action_txt}')
            problem_text='; '.join(issues) if issues else 'Scheduled PM - no abnormality recorded.'
            action_summary='; '.join(actions_done) if actions_done else 'PM checklist completed.'
            execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,'PM',now,problem_text,action_summary,now,f'Machine Type: {machine_type}; Checklist submitted'))
            if hot: execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,'PM related hot work','DRAFT'))
            if height: execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,'PM related height work','DRAFT'))
            st.success(f'PM Check Sheet saved for {mr.machine_name}. Actions + Remarks saved separately, Machine History updated, and required permit draft(s) created. Job ID: {jid}')
            current_job={'job_id':jid,'opened_at':now,'status':'OPEN','hot_work':int(hot),'height_work':int(height)}
            current_checks=[{'check_point':pt,'result':status,'action':action_txt,'remark':remark} for pt,status,action_txt,remark in results]
            current_pdf=build_pm_checksheet_pdf(current_job,current_checks,mr)
            st.download_button('📄 Download This PM Check Sheet PDF',data=current_pdf,
                file_name=f"PM_Check_Sheet_{jid.replace('/','-')}.pdf",mime='application/pdf',
                key=f'current_pm_pdf_{jid}',on_click='ignore')

        st.markdown('#### 📚 Saved PM Check Sheets - Download / Print')
        saved_pm_jobs=q("select * from jobs where machine_code=? and job_type='PM' order by opened_at desc",(code,))
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
                    file_name=f"PM_Check_Sheet_{saved_job_id.replace('/','-')}.pdf",mime='application/pdf',
                    key=f'saved_pm_pdf_{saved_job_id}',on_click='ignore')

with T[3]:
    st.subheader('Breakdown Maintenance — Start Linked BM Workflow'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='bmcode'); mr=machine_row(code); st.info(f"{mr.machine_name} | {mr.location} | {mr.make_model}")
    problem=st.text_area('Breakdown / Problem Details')
    cause=st.text_input('Immediate suspected cause (if known)')
    spares=st.text_input('Spares / material used or expected')
    st.markdown('#### Breakdown Timing')
    current_minute=datetime.now().time().replace(second=0,microsecond=0)
    bt1,bt2,bt3,bt4=st.columns(4)
    breakdown_start_date=bt1.date_input('Breakdown Start Date',value=TODAY,key='bm_start_date')
    breakdown_start_time=bt2.time_input('Breakdown Start Time',value=current_minute,key='bm_start_time')
    breakdown_end_date=bt3.date_input('Breakdown End Date',value=TODAY,key='bm_end_date')
    breakdown_end_time=bt4.time_input('Breakdown End Time',value=current_minute,key='bm_end_time')
    breakdown_start_dt=datetime.combine(breakdown_start_date,breakdown_start_time)
    breakdown_end_dt=datetime.combine(breakdown_end_date,breakdown_end_time)
    duration_seconds=(breakdown_end_dt-breakdown_start_dt).total_seconds()
    valid_breakdown_time=duration_seconds>=0
    downtime=round(max(duration_seconds,0)/3600,2)
    total_minutes=int(max(duration_seconds,0)//60)
    duration_hours,duration_minutes=divmod(total_minutes,60)
    if valid_breakdown_time:
        st.success(f'⏱️ Total Breakdown Time: {duration_hours} hour(s) {duration_minutes} minute(s) ({downtime:.2f} hours)')
    else:
        st.error('Breakdown End Date/Time, Start Date/Time से पहले नहीं हो सकती।')
    hot=st.checkbox('Hot work required')
    height=st.checkbox('Height work required')
    action=st.text_area('Action Taken / Planned')
    submit=st.button('Create BM Work Order & Linked Records',type='primary',key='bm_submit')
    if submit:
        if not valid_breakdown_time:
            st.error('Correct Breakdown Start and End date/time before saving.')
        elif not problem.strip():
            st.error('Breakdown / Problem Details field is required.')
        else:
            jid=new_id('BM'); start_iso=breakdown_start_dt.isoformat(timespec='minutes'); end_iso=breakdown_end_dt.isoformat(timespec='minutes'); execsql('insert into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'BM',code,mr.machine_name,mr.location,start_iso,problem,'CLOSED',int(hot),int(height),end_iso)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,'BM',start_iso,problem,action,end_iso,f'BM completed; Total downtime: {duration_hours}h {duration_minutes}m')); execsql('insert into breakdowns(job_id,machine_code,failure,cause,downtime_hr,spares,action,status) values(?,?,?,?,?,?,?,?)',(jid,code,problem,cause,downtime,spares,action,'CLOSED')); execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,start_iso,problem,cause,action,spares,downtime,'CLOSED',f'Completed: {end_iso}; Total downtime: {duration_hours}h {duration_minutes}m')); execsql('insert into whywhy(job_id,machine_code,problem,status) values(?,?,?,?)',(jid,code,problem,'DRAFT'))
            if hot:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,problem,'DRAFT'))
            if height:execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,problem,'DRAFT'))
            st.success(f'{jid} saved → Breakdown {start_iso} से {end_iso} तक चला। Total time: {duration_hours} hour(s) {duration_minutes} minute(s). Machine History + Breakdown History + Why-Why draft + applicable Permit draft(s) linked automatically.')

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
    # Keep the editable grid in session state. Without this, every widget rerun
    # reloads SQLite data and an unsaved row added with + disappears.
    table_state_key=f'bd_table_data_{code}'
    editor_key=f'bd_editor_{code}'
    if table_state_key not in st.session_state:
        existing=q('select id,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark from breakdown_activity_log where machine_code=? order by id',(code,))
        if len(existing)==0:
            existing=pd.DataFrame([{ 'id':None,'job_id':new_id('BM'),'activity_dt':datetime.now().isoformat(timespec='minutes'),'failure':'','cause':'','action':'','spares':'','downtime_hr':0.0,'status':'OPEN','remark':'' }])
        st.session_state[table_state_key]=existing.copy()
    edited=st.data_editor(st.session_state[table_state_key],num_rows='dynamic',use_container_width=True,hide_index=True,key=editor_key,column_config={
        'id':st.column_config.NumberColumn('ID',disabled=True),
        'job_id':st.column_config.TextColumn('Job / WO ID'),
        'activity_dt':st.column_config.TextColumn('Date / Time'),
        'failure':st.column_config.TextColumn('Problem / Failure',width='large'),
        'cause':st.column_config.TextColumn('Cause',width='medium'),
        'action':st.column_config.TextColumn('Activity / Action Taken',width='large'),
        'spares':st.column_config.TextColumn('Spares / Material',width='medium'),
        'downtime_hr':st.column_config.NumberColumn('Downtime Hr',min_value=0.0,step=0.25),
        'status':st.column_config.SelectboxColumn('Status',options=['OPEN','IN PROGRESS','CLOSED']),
        'remark':st.column_config.TextColumn('Remark',width='large')
    })
    # Capture added/edited rows after every rerun so the + row stays open.
    st.session_state[table_state_key]=edited.copy()
    csave,cinfo=st.columns([1,3])
    if csave.button('💾 Save Breakdown History',type='primary',use_container_width=True):
        cleaned=edited.copy(); cleaned=cleaned[cleaned[['failure','action','cause','spares','remark']].fillna('').astype(str).apply(lambda r: ''.join(r).strip()!='',axis=1)]
        execsql('delete from breakdown_activity_log where machine_code=?',(code,))
        for _,r in cleaned.iterrows():
            jid=str(_value_or(r.get('job_id'),new_id('BM'))); adt=str(_value_or(r.get('activity_dt'),datetime.now().isoformat(timespec='minutes'))); failure=str(_value_or(r.get('failure'),'')); cause=str(_value_or(r.get('cause'),'')); action=str(_value_or(r.get('action'),'')); spares=str(_value_or(r.get('spares'),'')); downtime=float(_value_or(r.get('downtime_hr'),0.0)); status=str(_value_or(r.get('status'),'OPEN')); remark=str(_value_or(r.get('remark'),''))
            execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,adt,failure,cause,action,spares,downtime,status,remark))
        st.success(f'{len(cleaned)} breakdown activity row(s) saved for {mr.machine_name}.')
        # Reload the just-saved database rows on the next run.
        st.session_state.pop(table_state_key,None)
        st.session_state.pop(editor_key,None)
        st.rerun()
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
