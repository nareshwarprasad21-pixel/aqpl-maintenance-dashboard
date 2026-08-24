import streamlit as st
import pandas as pd
import sqlite3, json, os, re, base64
from typing import Any
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

try:
    from supabase import create_client
except ImportError:
    create_client=None
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title='AQPL Maintenance Management', page_icon='🛠️', layout='wide')
BASE=os.path.dirname(__file__); DATA=os.path.join(BASE,'data'); DB=os.path.join(DATA,'maintenance.db')
LOGO_BASE64='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k7HSaU2i9dMdx6mrq7MKvbu7e82aNQsWLLjuuusIIffcc4/l8TRN4zgulUoAVq9effTo0euvv37RokVa6wcffNAGaFYU6uvr9+/f//Of/3zlypVf/vKXn3322UWLFg0cONBq4D+Gge/7di3Lly/v6Oi44oorrHNljKHWHVq9evWOHTuuuOKKIAg+9alPCSFuv/32NE3r6ursyufNm7dq1arrr7++u7t7yZIl11577b59+6ygFAqFzs5Oxlg2m7X+67JlywYPHjx9+vRJkyaNHTv2zjvvtKxk+UhKmclkJkyY8MMf/rC5ufnGG298/vnni8Wi53mWrLVQyJoy6+nWuK+mZOyYUqlUKBSsCKLPXlfrtNi4slqt1mKan/3sZ5zzT37yk5zzSy+99NChQ7t27eKcu67r+36hUDDG3H333cOHD581a9bMmTMnTZp07733xnFsednqgO7u7jvvvPOWW25Zv3799ddf/5WvfKVSqTDGLA/94cQcIZ7nSSlvv/325ubm6667LpPJVCoVQgi1AfTy5cuHDx/+iU98AsDUqVNnz579zDPPlEolIYRdUhAELS0tf/M3f7Nly5abbrqptbX1i1/8og35oijK5/P2KZVSq1atKhaL11xzjeX9G264oVKpWGa3PnIQBEqpKIpGjhz5ox/9qFAofPvb3965c2c2m7WT2MjTinZt4+a+fftc17UiYqHKZDJRFG3dutV1XcaY1bmnbUAYhqHN0thsj/XKDx48+OSTTy5cuHDkyJFJknzhC19oamq69dZb0zS1uiKO4wceeKBcLi9ZsoQxxhi79NJL0zR99NFHkySpr6+3EcDs2bNffvnlq666qrGx8eTJk7lcLpfLtbW1/ankpdZa6x/84AdSyiVLltibuVxOSkkB7N27d9++fblcbtWqVbfddtvSpUur1eqpU6fWrFnTN6sqhLDRx1/91V997nOfKxaL27dvd123qamps7PT6m4ATzzxRLFYPHr06IoVK2699daXXnpJKXX33XfXAkjf96vVquXKcePG3XLLLVrrzZs3V6tVy8528bXkV11d3Uc+8pGnnnrqd7/7ndVR3d3d11xzzb59+44fP75hw4aZM2famZubm0+ePGnhtEcYhps2bcpkMoMHDwZw7733MsbK5fIdd9xxxx13rFq1qrOzc+PGje3t7XYGY8zTTz9dLpcPHjx4zz33/PznPz927FgQBCtXrqwFtzU1eMMNN4waNWr16tXbtm0DMHDgQIv0H8Pg0KFDa9as+dCHPnTxxRfbVURRxDnnSZLce++9pVKpo6PjlltuiePY933f97PZ7F133XXVVVclSXL06NENGzYsXrzYcRyrEKwbYBVCW1tbU1OTTXJs27Zt69atxpilS5dms1ljTKlUam5u3rdv37p16y6++GKrdpuamjjnNjk4ZcqU733vezfffHOpVErTtGYMbIJMa10oFBYvXrxu3bpvfvObV1999cyZM0ePHn38+PFvfetbW7dubWpqWrx4sdWB06ZNe/bZZ3/xi1/ceOON/fv3D8Pwqaee2rVr14c//GHO+fHjx9evX885X7t27VNPPRUEQRRF9fX1WusVK1Z87WtfI4Rs3759586dhJBf/vKXjY2N1Wo1SZIgCLZt27Zp06ZZs2bFcVxfX28B6+npufnmmxcvXvyVr3zl6aefflMG4s0NjZx/4xvfcBxn0aJF9k59fX3vFvkTJ07MmTPnxz/+cVdXlzl9SCmfeOKJuXPn/vu//7sx5tvf/vbEiRPPO++8hQsXXnfddZdccsns2bOvv/56O/Kb3/zmtGnTrPP7+c9/fvbs2UIIm/22mUUhxIIFC6644go75pJLLvnc5z4nTx/2F1944YULL7zwwIEDNtdUc6XjOLYBx+bNmy+55JLzzjtv5syZF1100QUXXDBq1Kg5c+Y88MAD1lexf3/4wx9OmjRp2rRpc+fOnTVr1rhx4xYuXNjW1qaUWrp06aRJk1555ZVa3GM995tuumnatGmVSiWKok9/+tNz5861v2vtuT3/+Mc/vmDBArucCy644IYbbqg9+X333Xf++ef/8z//c+2OlPKqq65asGCBzQ7Zm0899dSMGTNmzpw5e/bsKVOmTJ069fzzz584ceKWLVvYtddeO3DgwMsuu6x///5RFDmOE4ah53kjRozwPK+pqWns2LE21I6iaMeOHQcPHhw7duz8+fOvv/56zrlNqb7vfe+bOnVqkiTVavWyyy6zkbr1XK2sNDc3jxw5sqWlRWs9dOjQwYMHT5gwwX7Xuiu5XO6yyy5zXbdQKNRu1rxGQkhLS8v8+fMBZLPZIAiam5unTZu2ffv2uXPnjh07lhBic8UzZ84cOHBgqVQyxowZM8ZSx/d9x3GOHDkyderUuXPnWrMhhLBKb9iwYcOGDbPWmHM+f/784cOHU0pt/tluZGtpaRk0aNCYMWOklHV1dRMmTLDhEWNs1KhRQRAEQTBq1Cibz4jjOJfLjRkzZsSIEa7rlstlz/M2bdo0bdq0c889d+LEidOnT58xY8bkyZOnT58+bdo0GGNaW1trKb2+0FketIxsT8IwtGiHYVi7bznXcmJnZ2eNd/pGzlLK7u5ueyeKoiRJ7K/U+N1aafMnD1tNql2eOnVqwYIFX//610+ePFmbre8AY0xPT09NSt40f5qmdrAQoqenp1gs2vHWWf/9hymXy3Z8GIZ2wtoRhmG5XO5LOiFETdr6PlKtbtOX4MSeWefHpudsGtUyhVXNNjHSt0JQs9KWX2rFjZo2j+PYeodCiFqW0SZ+32Spaq9NeeP7tP7oEcexrYr4vt/W1pbNZvP5fN8ntHB6nmfNvtVstWeoZXbfVHp6U0I+jmPr11JKwzC0RZi+1S27FhtF1Shj5b6W1q6FijXi2GpYLftkL/8fLGjYAgBb6FoAAAAASUVORK5CYII='

st.markdown('''<style>
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#07111f,#0b1728);color:#eef4ff}
[data-testid="stSidebar"]{background:#091426;border-right:1px solid #22314b}
.block-container{max-width:1550px;padding-top:1.4rem}.hero{padding:20px 24px;border:1px solid #263958;border-radius:18px;background:linear-gradient(135deg,#10213b,#0b1728);margin-bottom:14px}
.hero h1{margin:0;font-size:2rem}.sub{color:#9fb0c9}.kpi{padding:16px;border-radius:15px;background:#101f35;border:1px solid #243754;min-height:108px}.kpi b{font-size:1.7rem}.green{border-left:5px solid #22c55e}.yellow{border-left:5px solid #eab308}.red{border-left:5px solid #ef4444}.purple{border-left:5px solid #8b5cf6}
@media(max-width:700px){.hero-brand{flex-direction:column;align-items:flex-start!important}.hero h1{font-size:1.45rem}}
.stTabs [data-baseweb="tab-list"]{gap:7px;background:#0d1b30;padding:6px;border-radius:13px}.stTabs [data-baseweb="tab"]{height:44px;padding:0 14px;font-weight:700}.stTabs [aria-selected="true"]{background:#5b43d6;color:white;border-radius:9px}
[data-testid="stDataFrame"],[data-testid="stDataEditor"]{border:1px solid #263958;border-radius:12px;overflow:hidden}.flow{padding:12px 15px;border-radius:12px;background:#101f35;border:1px solid #263958;margin:7px 0}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,[data-testid="stTimeInput"] input{color:#0b1220 !important;background-color:#f8fafc !important;-webkit-text-fill-color:#0b1220 !important;caret-color:#0b1220 !important;font-weight:500}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder{color:#64748b !important;-webkit-text-fill-color:#64748b !important;opacity:1 !important}
[data-testid="stTextInput"] label,[data-testid="stTextArea"] label,[data-testid="stNumberInput"] label,[data-testid="stDateInput"] label,[data-testid="stTimeInput"] label{color:#dbeafe !important}
</style>''',unsafe_allow_html=True)

@st.cache_data
def load_static(cache_version):
    m=pd.read_csv(os.path.join(DATA,'machines.csv')).fillna('')
    p=pd.read_csv(os.path.join(DATA,'pm_plan.csv')); p['scheduled_date']=pd.to_datetime(p['scheduled_date']).dt.date
    with open(os.path.join(DATA,'checklists.json'),encoding='utf-8') as f:c=json.load(f)
    return m,p,c
STATIC_MACH,PLAN,CHECKS=load_static('2026-08-24-belt-conveyor-v1')
MACH=STATIC_MACH.copy()

TABLE_COLUMNS={
    'equipment_master':['machine_code','machine_name','make_model','capacity','location','is_active','created_at','updated_at'],
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
    CREATE TABLE IF NOT EXISTS equipment_master(machine_code TEXT PRIMARY KEY,machine_name TEXT NOT NULL,make_model TEXT DEFAULT '',capacity TEXT DEFAULT '',location TEXT DEFAULT '',is_active INTEGER DEFAULT 1,created_at TEXT,updated_at TEXT);
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

def load_equipment_master():
    """Load the editable master; seed the local fallback from the bundled CSV."""
    rows=q('select machine_code,machine_name,make_model,capacity,location,is_active from equipment_master order by machine_name')
    if rows.empty and not USE_SUPABASE:
        now=datetime.now().isoformat(timespec='seconds')
        for _,machine in STATIC_MACH.iterrows():
            execsql('insert or replace into equipment_master(machine_code,machine_name,make_model,capacity,location,is_active,created_at,updated_at) values(?,?,?,?,?,?,?,?)',(machine.machine_code,machine.machine_name,machine.make_model,machine.capacity,machine.location,1,now,now))
        rows=q('select machine_code,machine_name,make_model,capacity,location,is_active from equipment_master order by machine_name')
    if rows.empty:
        fallback=STATIC_MACH.copy(); fallback['is_active']=True; return fallback
    rows['is_active']=rows['is_active'].fillna(True).astype(bool)
    return rows

EQUIPMENT=load_equipment_master()
MACH=EQUIPMENT[EQUIPMENT.is_active].drop(columns=['is_active']).reset_index(drop=True)

def deduplicate_pm_checks(checks):
    """Return one merged row per check point, preserving the checklist order."""
    records=checks.to_dict('records') if isinstance(checks,pd.DataFrame) else list(checks)
    merged={}
    for item in records:
        row=dict(item)
        check_point=str(_value_or(row.get('check_point'),'')).strip()
        key=check_point.casefold()
        if not key:
            continue
        if key not in merged:
            merged[key]={'check_point':check_point,'result':'','action':'','remark':''}
        # Repeated saves can contain progressively completed fields. Keep the
        # latest non-empty value from every batch instead of printing all rows.
        for field in ('result','action','remark'):
            value=row.get(field,'')
            if value is not None and str(value).strip():
                merged[key][field]=value
    return list(merged.values())

def pdf_brand_header(title_style,total_width=184*mm):
    """Build a balanced document header with the official company logo."""
    logo=RLImage(BytesIO(base64.b64decode(LOGO_BASE64)),width=27*mm,height=15.7*mm)
    side_width=32*mm
    header=Table(
        [[logo,Paragraph('ASIAN QUAARTZ PVT LTD',title_style),'']],
        colWidths=[side_width,total_width-(2*side_width),side_width]
    )
    header.hAlign='CENTER'
    header.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ALIGN',(0,0),(0,0),'LEFT'),
        ('ALIGN',(1,0),(1,0),'CENTER'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),2)
    ]))
    return header

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
                          author='Asian Quaartz Pvt Ltd')
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
        pdf_brand_header(title_style),
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
    records=deduplicate_pm_checks(checks)
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

def build_breakdown_report_pdf(job,breakdown,machine):
    """Return a printable A4 breakdown maintenance report."""
    def val(source,key,default=''):
        try:value=source.get(key,default)
        except AttributeError:value=default
        if value is None:return default
        try:
            if pd.isna(value):return default
        except (TypeError,ValueError):pass
        return str(value)

    regular='Helvetica'; bold='Helvetica-Bold'
    font_paths=[
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/dejavu/DejaVuSans.ttf','/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf')]
    for regular_path,bold_path in font_paths:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont('AQPLBDSans',regular_path)); pdfmetrics.registerFont(TTFont('AQPLBDSansBold',bold_path))
                regular='AQPLBDSans'; bold='AQPLBDSansBold'; break
            except Exception:pass

    downtime=float(val(breakdown,'downtime_hr','0') or 0)
    total_minutes=round(downtime*60); duration_hours,duration_minutes=divmod(total_minutes,60)
    buffer=BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=15*mm,bottomMargin=16*mm,title=f"Breakdown Report - {val(breakdown,'job_id')}",author='Asian Quaartz Pvt Ltd')
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle('BDTitle',parent=styles['Title'],fontName=bold,fontSize=15,leading=18,textColor=colors.HexColor('#10213b'),alignment=TA_CENTER,spaceAfter=2*mm)
    subtitle_style=ParagraphStyle('BDSubtitle',parent=styles['Heading2'],fontName=bold,fontSize=11,leading=14,textColor=colors.HexColor('#b91c1c'),alignment=TA_CENTER,spaceAfter=5*mm)
    body=ParagraphStyle('BDBody',parent=styles['BodyText'],fontName=regular,fontSize=8.5,leading=11,textColor=colors.HexColor('#111827'))
    body_bold=ParagraphStyle('BDBold',parent=body,fontName=bold)
    story=[pdf_brand_header(title_style),Paragraph('BREAKDOWN MAINTENANCE REPORT',subtitle_style)]
    rows=[
        ['Machine Name',val(machine,'machine_name'),'Machine Code',val(machine,'machine_code')],
        ['Location',val(machine,'location'),'Make / Model',val(machine,'make_model')],
        ['Job / WO ID',val(breakdown,'job_id'),'Status',val(breakdown,'status')],
        ['Breakdown Start',val(job,'opened_at',val(breakdown,'activity_dt')),'Breakdown End',val(job,'closed_at')],
        ['Total Breakdown Time',f'{duration_hours} hour(s) {duration_minutes} minute(s)', 'Downtime Hours',f'{downtime:.2f}']]
    meta=[]
    for row in rows:
        meta.append([Paragraph(f'<b>{escape(row[0])}</b>',body_bold),Paragraph(escape(row[1]),body),Paragraph(f'<b>{escape(row[2])}</b>',body_bold),Paragraph(escape(row[3]),body)])
    table=Table(meta,colWidths=[34*mm,57*mm,34*mm,57*mm]); table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#94a3b8')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e2e8f0')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#e2e8f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])); story.extend([table,Spacer(1,6*mm)])
    details=[('Breakdown / Problem Details',val(breakdown,'failure',val(job,'problem'))),('Immediate / Root Cause',val(breakdown,'cause')),('Spares / Material Used',val(breakdown,'spares')),('Action Taken / Work Done',val(breakdown,'action')),('Remarks',val(breakdown,'remark'))]
    for label,value in details:
        story.extend([Paragraph(escape(label),body_bold),Table([[Paragraph(escape(value or '-'),body)]],colWidths=[182*mm],style=TableStyle([('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#94a3b8')),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f8fafc')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])),Spacer(1,4*mm)])
    signatures=[[Paragraph('<b>Prepared By</b>',body_bold),Paragraph('<b>Checked By</b>',body_bold),Paragraph('<b>Approved By</b>',body_bold)],[Paragraph('<br/><br/>Name &amp; Sign: _______________',body),Paragraph('<br/><br/>Maintenance Engineer: ________',body),Paragraph('<br/><br/>HOD / Plant Head: ___________',body)]]
    sign_table=Table(signatures,colWidths=[60.7*mm]*3); sign_table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#64748b')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])); story.append(sign_table)
    def footer(canvas,document):
        canvas.saveState(); canvas.setFont(regular,7); canvas.setFillColor(colors.HexColor('#64748b')); canvas.drawString(14*mm,8*mm,f"Document: AQPL/MAINT/BM | Job: {val(breakdown,'job_id')}"); canvas.drawRightString(A4[0]-14*mm,8*mm,f"Page {document.page}"); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return buffer.getvalue()

def build_machine_history_pdf(history_rows,machine,activity_type):
    """Return the selected machine's complete filtered PM/BM history as PDF."""
    def val(source,key,default=''):
        try:value=source.get(key,default)
        except AttributeError:value=default
        if value is None:return default
        try:
            if pd.isna(value):return default
        except (TypeError,ValueError):pass
        return str(value)

    regular='Helvetica'; bold='Helvetica-Bold'
    regular_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if os.path.exists(regular_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont('AQPLHistorySans',regular_path))
            pdfmetrics.registerFont(TTFont('AQPLHistorySansBold',bold_path))
            regular='AQPLHistorySans'; bold='AQPLHistorySansBold'
        except Exception:pass

    buffer=BytesIO(); page_size=landscape(A4)
    doc=SimpleDocTemplate(buffer,pagesize=page_size,rightMargin=10*mm,leftMargin=10*mm,
        topMargin=12*mm,bottomMargin=15*mm,
        title=f"{activity_type} Machine History - {val(machine,'machine_code')}",
        author='Asian Quaartz Pvt Ltd')
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle('HistoryTitle',parent=styles['Title'],fontName=bold,
        fontSize=15,leading=18,textColor=colors.HexColor('#10213b'),alignment=TA_CENTER,spaceAfter=2*mm)
    subtitle_style=ParagraphStyle('HistorySubtitle',parent=styles['Heading2'],fontName=bold,
        fontSize=11,leading=14,textColor=colors.HexColor('#1d4ed8'),alignment=TA_CENTER,spaceAfter=4*mm)
    body=ParagraphStyle('HistoryBody',parent=styles['BodyText'],fontName=regular,fontSize=7,leading=9,textColor=colors.HexColor('#111827'))
    body_bold=ParagraphStyle('HistoryBold',parent=body,fontName=bold)
    header_style=ParagraphStyle('HistoryHeader',parent=body_bold,textColor=colors.white,alignment=TA_CENTER)
    story=[pdf_brand_header(title_style,total_width=277*mm),Paragraph(f'{escape(activity_type)} MACHINE HISTORY REPORT',subtitle_style)]
    machine_meta=[
        [Paragraph('<b>Machine Name</b>',body_bold),Paragraph(escape(val(machine,'machine_name')),body),
         Paragraph('<b>Machine Code</b>',body_bold),Paragraph(escape(val(machine,'machine_code')),body)],
        [Paragraph('<b>Location</b>',body_bold),Paragraph(escape(val(machine,'location')),body),
         Paragraph('<b>Make / Model</b>',body_bold),Paragraph(escape(val(machine,'make_model')),body)]
    ]
    meta=Table(machine_meta,colWidths=[30*mm,108.5*mm,30*mm,108.5*mm])
    meta.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.45,colors.HexColor('#94a3b8')),
        ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e2e8f0')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#e2e8f0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.extend([meta,Spacer(1,5*mm)])
    rows=[[Paragraph('<b>S.No.</b>',header_style),Paragraph('<b>Job / Work ID</b>',header_style),
        Paragraph('<b>Start Date-Time</b>',header_style),Paragraph('<b>Problem / Activity</b>',header_style),
        Paragraph('<b>Action Taken / Work Done</b>',header_style),Paragraph('<b>Completion Date-Time</b>',header_style),
        Paragraph('<b>Remark / Observation</b>',header_style)]]
    records=history_rows.to_dict('records') if isinstance(history_rows,pd.DataFrame) else list(history_rows)
    for index,row in enumerate(records,1):
        rows.append([Paragraph(str(index),body),Paragraph(escape(val(row,'job_id')),body),
            Paragraph(escape(val(row,'start_dt')),body),Paragraph(escape(val(row,'problem')),body),
            Paragraph(escape(val(row,'action_taken')),body),Paragraph(escape(val(row,'restart_dt')),body),
            Paragraph(escape(val(row,'remark')),body)])
    history_table=Table(rows,colWidths=[10*mm,35*mm,30*mm,55*mm,55*mm,30*mm,62*mm],repeatRows=1)
    history_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#10213b')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#94a3b8')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ALIGN',(0,0),(0,-1),'CENTER'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
        ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(history_table)
    def footer(canvas,document):
        canvas.saveState(); canvas.setFont(regular,7); canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(10*mm,7*mm,f"Document: AQPL/MAINT/HISTORY | Machine: {val(machine,'machine_code')}")
        canvas.drawRightString(page_size[0]-10*mm,7*mm,f'Page {document.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()

def new_id(kind):
    """Generate readable IST-based PM/BM IDs with a daily running sequence."""
    now_ist=datetime.now(ZoneInfo('Asia/Kolkata'))
    if kind in ('PM','BM'):
        prefix=f"AQPL-{kind}-{now_ist:%Y%m%d}"
        existing=q('select job_id from jobs where job_type=?',(kind,))
        sequences=[]
        if len(existing):
            for job_id in existing.job_id.fillna('').astype(str):
                # Only the new three-digit suffix participates in sequencing;
                # legacy time-based IDs such as -123334 are ignored.
                match=re.fullmatch(rf'{re.escape(prefix)}-(\d{{3}})',job_id)
                if match:sequences.append(int(match.group(1)))
        return f"{prefix}-{max(sequences,default=0)+1:03d}"
    return f"AQPL-{kind}-{now_ist:%Y%m%d-%H%M%S}"

def resequence_daily_bm_job_ids(deleted_job_id):
    """Close gaps in the three-digit BM sequence for the deleted job's date."""
    match=re.fullmatch(r'AQPL-BM-(\d{8})-(\d{3})',str(deleted_job_id))
    if not match:
        return {}
    date_part=match.group(1)
    prefix=f'AQPL-BM-{date_part}-'
    jobs=q("select job_id,opened_at from jobs where job_type='BM' order by opened_at asc")
    daily=[]
    for _,row in jobs.iterrows():
        job_id=str(row.job_id)
        seq_match=re.fullmatch(rf'{re.escape(prefix)}(\d{{3}})',job_id)
        if seq_match:
            daily.append((job_id,str(_value_or(row.opened_at,'')),int(seq_match.group(1))))
    daily.sort(key=lambda item:(item[1],item[2]))
    renamed={}
    linked_tables=['pm_checks','permits','whywhy','breakdown_activity_log','breakdowns','history','jobs']
    for sequence,(old_job_id,_,_) in enumerate(daily,1):
        new_job_id=f'{prefix}{sequence:03d}'
        if old_job_id==new_job_id:
            continue
        for table in linked_tables:
            execsql(f'update {table} set job_id=? where job_id=?',(new_job_id,old_job_id))
        renamed[old_job_id]=new_job_id
    return renamed

def machine_row(code): return MACH[MACH.machine_code==code].iloc[0]

def machine_type_for(machine):
    """Return the equipment type instead of incorrectly showing its location."""
    machine_name=str(_value_or(machine.machine_name,'')).strip().lower()
    machine_code=str(_value_or(machine.machine_code,'')).strip().lower()
    if 'compressor' in machine_name or '/comp-' in machine_code:
        return 'AIR COMPRESSOR'
    if 'b.c.' in machine_name:
        return 'BELT CONVEYOR'
    return str(_value_or(machine.location,''))

def suggest_sheet(name):
    n=name.lower(); rules=[('jaw','Jaw crusher'),('secondary cone','sec cone cr'),('tertiary cone','Tertiary cone crusher'),('primary class','Vibro acreen'),('scrubber','scrubber'),('washing class','washing screen'),('de-water','DEWAT.SCREEN'),('heater-1','Heter-1'),('heater-2','Heter-2'),('heater-3','Heter-3'),('primary ball','P.B.MILL'),('secondary ball','S.B.mill'),('primary dynamic','P.Dy.seperator'),('secondary dynamic','S.dy.seprator'),('primary bag','P.baghouse'),('secondary bag','s.baghouse'),('primary vibro','P.vibroscreen'),('secondary vibro','S.vibro screen'),('magnetic','magnetic sep.-1'),('eot crane-1','EOT CRANE-1'),('eot crane-2','EOT CRANE-2'),('eot crane-3','EOT CRAN-3'),('compressor-1','compressor-1'),('compressor-2','compressor-2'),('compressor-3','compressor-3'),('compressor-4','compressor-4'),('compressor-5','compressor-4'),('chiller-1','chiller-1'),('chiller-2','chiller-2'),('chiller-3','chiller-3')]
    for k,s in rules:
        if k in n:return s
    return ''
BELT_CONVEYOR_CODES={
    'AQPL/TER BC-7','AQPL/TER BC-8','AQPL/TER BC-9',
    'AQPL/TER BC-10','AQPL/TER BC-11','AQPL/TER BC-12',
    'AQPL/TER BC-13','AQPL/TER BC-14','AQPL/TER H-7'
}

def checklist_for(code):
    r=q('select sheet_name from checklist_map where machine_code=?',(code,))
    if len(r) and r.iloc[0,0] in CHECKS:return r.iloc[0,0]
    if code in BELT_CONVEYOR_CODES:return 'BELT CONVEYOR'
    return suggest_sheet(machine_row(code).machine_name)

def top_header():
    logo_html=f'<img src="data:image/png;base64,{LOGO_BASE64}" alt="Asian Quaartz Logo" style="width:105px;height:61px;object-fit:contain;background:white;border-radius:8px;padding:3px">'
    st.markdown(f'''<div class="hero hero-brand" style="display:flex;align-items:center;gap:20px">
        {logo_html}<div><h1>ASIAN QUAARTZ PVT LTD — Maintenance Management Dashboard</h1>
        <div class="sub">PM • Breakdown • Machine History • Work Orders • Height/Hot Work Permits • Why-Why RCA</div></div>
        </div>''',unsafe_allow_html=True)
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
            def select_planned_pm_machine():
                selected=st.session_state.get('pm_plan_machine_pick','')
                if selected:
                    st.session_state['pmcode']=selected.rsplit(' | ',1)[-1]
            selected_machine=st.selectbox(
                'Select machine scheduled on this date',scheduled_options,
                key='pm_plan_machine_pick',on_change=select_planned_pm_machine
            )
            selected_code=selected_machine.split(' | ')[-1]
            # Initialise once. Afterwards the PM Check Sheet selector remains
            # under the user's control instead of being reset on every rerun.
            if 'pmcode' not in st.session_state:
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
        pm_key=re.sub(r'[^A-Za-z0-9_-]+','_',code)
        m1,m2,m3,m4=st.columns(4)
        m1.text_input('Machine Name',value=str(mr.machine_name),disabled=True,key=f'pm_machine_name_{pm_key}')
        m2.text_input('Machine Number / Code',value=code,disabled=True,key=f'pm_machine_code_{pm_key}')
        maintenance_date=m3.date_input('Maintenance Date',value=TODAY,key='pm_maintenance_date')
        machine_type=m4.text_input('Machine Type',value=machine_type_for(mr),key=f'pm_machine_type_{pm_key}')
        d1,d2=st.columns([2,1])
        d1.info(f'Make / Model: {mr.make_model} | Location: {mr.location}')
        jid=d2.text_input('PM Work Order / Job ID',value=new_id('PM'),key=f'pmjid_{pm_key}')
        st.markdown('#### Checklist Details')
        st.caption('Actual AQPL format की तरह हर check point के लिए Status, Action और Remark अलग-अलग भरें।')
        results=[]
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
            st.markdown('#### Safety / Permit Requirement')
            hot=st.checkbox('Hot work involved',key=f'{pm_key}_hot')
            height=st.checkbox('Height work involved',key=f'{pm_key}_height')
            submit=st.form_submit_button('Submit PM Check Sheet & Update History',type='primary')
        if submit:
            now=datetime.combine(maintenance_date,datetime.now().time().replace(second=0,microsecond=0)).isoformat(timespec='minutes')
            execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,'PM',code,mr.machine_name,mr.location,now,'Scheduled preventive maintenance','OPEN',int(hot),int(height),None))
            # A PM Job ID represents one checklist. Re-saving replaces its
            # linked rows instead of appending another copy of every point.
            execsql('delete from pm_checks where job_id=?',(jid,))
            execsql('delete from history where job_id=?',(jid,))
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
            existing_hot=q('select id from permits where job_id=? and permit_type=?',(jid,'HOT WORK'))
            existing_height=q('select id from permits where job_id=? and permit_type=?',(jid,'HEIGHT WORK'))
            if hot and not len(existing_hot): execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HWP'),jid,'HOT WORK',code,'PM related hot work','DRAFT'))
            if height and not len(existing_height): execsql('insert into permits(permit_no,job_id,permit_type,machine_code,activity,status) values(?,?,?,?,?,?)',(new_id('HTP'),jid,'HEIGHT WORK',code,'PM related height work','DRAFT'))
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
    history_key=re.sub(r'[^A-Za-z0-9_-]+','_',f'{code}_{activity_type}')
    current_history_time=datetime.now().time().replace(second=0,microsecond=0)
    # Apply a delete-triggered renumber before the Job ID widget is created.
    pending_renames=st.session_state.pop('bm_job_id_renumber_map',{})
    history_job_key=f'{history_key}_job_id'
    current_draft_job=st.session_state.get(history_job_key)
    if current_draft_job in pending_renames:
        st.session_state[history_job_key]=pending_renames[current_draft_job]
    # Keep the form values on Calculate/Save reruns. A machine/activity-specific
    # form and widget keys prevent current time/defaults from replacing values.
    with st.form(f'manual_history_form_{history_key}',clear_on_submit=False):
        c1,c2,c3=st.columns([1.4,1,1])
        jid=c1.text_input('Job / Work Order ID',value=default_jid,key=history_job_key)
        start_date=c2.date_input('Start Date',value=TODAY,key=f'{history_key}_start_date')
        start_time=c3.time_input('Start Time',value=current_history_time,key=f'{history_key}_start_time')
        problem=st.text_area('Problem / Maintenance Activity',key=f'{history_key}_problem',placeholder='PM activity performed or breakdown/problem details')
        action=st.text_area('Action Taken / Work Done',key=f'{history_key}_action',placeholder='Inspection, repair, replacement, adjustment, lubrication, etc.')
        r1,r2=st.columns(2)
        restart_date=r1.date_input('Restart / Completion Date',value=TODAY,key=f'{history_key}_restart_date')
        restart_time=r2.time_input('Restart / Completion Time',value=current_history_time,key=f'{history_key}_restart_time')
        remark=st.text_area('Remark / Observation',key=f'{history_key}_remark')
        start_dt_value=datetime.combine(start_date,start_time); restart_dt_value=datetime.combine(restart_date,restart_time); duration_seconds=(restart_dt_value-start_dt_value).total_seconds(); valid_history_time=duration_seconds>=0; downtime=round(max(duration_seconds,0)/3600,2); total_history_minutes=int(max(duration_seconds,0)//60); history_hours,history_minutes=divmod(total_history_minutes,60)
        if activity_type=='BM':
            b1,b2=st.columns(2); cause=b1.text_input('Breakdown Cause / Suspected Cause',key=f'{history_key}_cause'); b2.text_input('Calculated Downtime',value=f'{history_hours} hour(s) {history_minutes} minute(s) ({downtime:.2f} hours)',disabled=True); spares=st.text_input('Spares / Material Used',key=f'{history_key}_spares')
        else:cause=''; spares=''
        fb1,fb2=st.columns(2)
        calculate_history=fb1.form_submit_button('⏱️ Calculate Downtime',use_container_width=True)
        save_history=fb2.form_submit_button(f'Save {activity_type} History',type='primary',use_container_width=True)
    if calculate_history:
        if valid_history_time:st.success(f'Total time: {history_hours} hour(s) {history_minutes} minute(s) ({downtime:.2f} hours). आपकी भरी हुई entries सुरक्षित हैं।')
        else:st.error('Restart / Completion Date-Time, Start Date-Time से पहले नहीं हो सकती। Entries सुरक्षित हैं; time सही करें।')
    if save_history:
        if not valid_history_time:st.error('Restart / Completion Date-Time, Start Date-Time से पहले नहीं हो सकती।')
        elif not problem.strip():st.error('Problem / Maintenance Activity field is required.')
        elif not action.strip():st.error('Action Taken / Work Done field is required.')
        else:
            start_dt=start_dt_value.isoformat(timespec='minutes'); restart_dt=restart_dt_value.isoformat(timespec='minutes'); execsql('insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)',(jid,activity_type,code,mr.machine_name,mr.location,start_dt,problem,'CLOSED',0,0,restart_dt)); execsql('insert into history(job_id,machine_code,maintenance_type,start_dt,problem,action_taken,restart_dt,remark) values(?,?,?,?,?,?,?,?)',(jid,code,activity_type,start_dt,problem,action,restart_dt,remark))
            if activity_type=='BM':
                execsql('insert into breakdowns(job_id,machine_code,failure,cause,downtime_hr,spares,action,status) values(?,?,?,?,?,?,?,?)',(jid,code,problem,cause,downtime,spares,action,'CLOSED')); execsql('insert into breakdown_activity_log(machine_code,job_id,activity_dt,failure,cause,action,spares,downtime_hr,status,remark) values(?,?,?,?,?,?,?,?,?,?)',(code,jid,start_dt,problem,cause,action,spares,downtime,'CLOSED',remark)); existing=q('select id from whywhy where job_id=?',(jid,));
                if not len(existing):execsql('insert into whywhy(job_id,machine_code,problem,status) values(?,?,?,?)',(jid,code,problem,'DRAFT'))
                st.success(f'BM history saved for {mr.machine_name}. Breakdown History and Why-Why draft also linked automatically. Job ID: {jid}')
            else:st.success(f'PM history saved for {mr.machine_name}. Job ID: {jid}')
    st.markdown('### 📚 Saved History')
    delete_flash_key=f'history_delete_flash_{code}_{activity_type}'
    if delete_flash_key in st.session_state:
        st.success(st.session_state.pop(delete_flash_key))
    history_view=q('select job_id,maintenance_type,start_dt,problem,action_taken,restart_dt,remark from history where machine_code=? and maintenance_type=? order by id desc',(code,activity_type)); st.dataframe(history_view,use_container_width=True,hide_index=True)
    if len(history_view):
        machine_history_pdf=build_machine_history_pdf(history_view,mr,activity_type)
        safe_machine_code=re.sub(r'[^A-Za-z0-9_-]+','-',code).strip('-')
        st.download_button(
            f'⬇️ Download {activity_type} Machine History PDF',
            data=machine_history_pdf,
            file_name=f'{activity_type}_Machine_History_{safe_machine_code}.pdf',
            mime='application/pdf',key=f'machine_history_pdf_{history_key}',
            type='primary',on_click='ignore',use_container_width=True
        )
        st.caption(f'इस PDF में {mr.machine_name} की सभी saved {activity_type} history entries शामिल हैं।')
        st.markdown('#### 🗑️ Delete Saved Entry')
        delete_options=[f"{r.job_id} | {str(_value_or(r.problem,'Maintenance entry'))[:60]}" for _,r in history_view.iterrows()]
        selected_delete=st.selectbox('Select Job ID to delete',delete_options,key=f'history_delete_pick_{code}_{activity_type}')
        delete_job_id=selected_delete.split(' | ')[0]
        st.warning(f'{delete_job_id} delete करने पर इससे linked Machine History, Breakdown History, Why-Why, Work Order, Permit और report records भी हटेंगे। यह action वापस नहीं होगा।')
        confirm_delete=st.checkbox(f'I confirm: delete {delete_job_id}',key=f'history_delete_confirm_{code}_{activity_type}_{delete_job_id}')
        if st.button('🗑️ Delete Selected Entry',type='secondary',disabled=not confirm_delete,key=f'history_delete_button_{code}_{activity_type}'):
            # Delete child/link records first, then the parent work order.
            for linked_table in ['pm_checks','permits','whywhy','breakdown_activity_log','breakdowns','history','jobs']:
                execsql(f'delete from {linked_table} where job_id=?',(delete_job_id,))
            renamed=resequence_daily_bm_job_ids(delete_job_id) if activity_type=='BM' else {}
            st.session_state['bm_job_id_renumber_map']=renamed
            renumber_note=''
            if renamed:
                renumber_note=' Remaining daily BM Job IDs sequence में renumber हो गई हैं: '+', '.join(f'{old} → {new}' for old,new in renamed.items())+'.'
            st.session_state[delete_flash_key]=f'{delete_job_id} और उसके linked records successfully delete हो गए। बाकी entries सुरक्षित हैं।{renumber_note}'
            st.rerun()

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

    st.markdown('### 📄 Download Breakdown Report')
    saved_breakdowns=q('select * from breakdowns where machine_code=? order by id desc',(code,))
    if saved_breakdowns.empty:
        st.info('इस machine की saved breakdown report अभी उपलब्ध नहीं है।')
    else:
        report_options=[]
        for _,bd_row in saved_breakdowns.iterrows():
            report_options.append(f"{bd_row.job_id} | {str(_value_or(bd_row.failure,'Breakdown'))[:55]}")
        selected_report=st.selectbox('Select saved Breakdown Job / Work Order',report_options,key=f'breakdown_pdf_job_{code}')
        selected_job_id=selected_report.split(' | ')[0]
        selected_breakdown=saved_breakdowns[saved_breakdowns.job_id==selected_job_id].iloc[0].to_dict()
        job_rows=q('select * from jobs where job_id=?',(selected_job_id,))
        selected_job=job_rows.iloc[0].to_dict() if len(job_rows) else {'job_id':selected_job_id,'opened_at':'','closed_at':'','status':selected_breakdown.get('status','')}
        activity_rows=q('select * from breakdown_activity_log where job_id=? order by id desc',(selected_job_id,))
        if len(activity_rows):
            activity=activity_rows.iloc[0].to_dict()
            selected_breakdown['activity_dt']=activity.get('activity_dt','')
            selected_breakdown['remark']=activity.get('remark','')
        breakdown_pdf=build_breakdown_report_pdf(selected_job,selected_breakdown,mr)
        st.download_button('⬇️ Download Breakdown Report PDF',data=breakdown_pdf,file_name=f"Breakdown_Report_{selected_job_id.replace('/','-')}.pdf",mime='application/pdf',key=f'breakdown_pdf_download_{selected_job_id}',type='primary',on_click='ignore')
        st.caption('PDF में machine details, start/end time, total downtime, problem, cause, spares, action, status और signatures शामिल हैं।')

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

with T[8]:
    st.subheader('Machine / Equipment Master')
    st.caption('Equipment Master अब Supabase में permanently save होता है। Active machines ही PM, Breakdown और History dropdowns में दिखाई देंगी।')
    total_master_machines=len(EQUIPMENT)
    active_master_machines=int(EQUIPMENT.is_active.fillna(False).astype(bool).sum())
    inactive_master_machines=total_master_machines-active_master_machines
    mc1,mc2,mc3=st.columns(3)
    mc1.metric('Total Machines in Master',total_master_machines)
    mc2.metric('Active Machines',active_master_machines)
    mc3.metric('Inactive Machines',inactive_master_machines)
    master_view=EQUIPMENT.rename(columns={'machine_name':'Machine Name','machine_code':'Machine Code','make_model':'Make / Model','capacity':'Capacity','location':'Location','is_active':'Active'}).reset_index(drop=True)
    master_view.insert(0,'S.No.',range(1,total_master_machines+1))
    st.dataframe(master_view,use_container_width=True,hide_index=True)
    master_mode=st.radio('Equipment Master Action',['➕ Add New Machine','✏️ Edit / Activate / Inactivate'],horizontal=True,key='equipment_master_action')
    if master_mode=='➕ Add New Machine':
        with st.form('add_equipment_master_form',clear_on_submit=True):
            a1,a2=st.columns(2); new_code=a1.text_input('Machine Code *',placeholder='Example: AQPL/PUMP-01'); new_name=a2.text_input('Machine Name *')
            a3,a4,a5=st.columns(3); new_make=a3.text_input('Make / Model'); new_capacity=a4.text_input('Capacity'); new_location=a5.text_input('Location *')
            new_active=st.checkbox('Active',value=True); add_machine=st.form_submit_button('💾 Add Machine',type='primary')
        if add_machine:
            clean_code=new_code.strip().upper(); clean_name=new_name.strip(); clean_location=new_location.strip()
            if not clean_code or not clean_name or not clean_location:st.error('Machine Code, Machine Name और Location required हैं।')
            elif clean_code in EQUIPMENT.machine_code.astype(str).tolist():st.error(f'{clean_code} पहले से Equipment Master में मौजूद है। Edit option उपयोग करें।')
            else:
                now=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(timespec='seconds'); execsql('insert into equipment_master(machine_code,machine_name,make_model,capacity,location,is_active,created_at,updated_at) values(?,?,?,?,?,?,?,?)',(clean_code,clean_name,new_make.strip(),new_capacity.strip(),clean_location,bool(new_active),now,now)); st.success(f'{clean_name} ({clean_code}) Equipment Master में add हो गई।'); st.rerun()
    else:
        edit_code=st.selectbox('Select Machine Code to edit',EQUIPMENT.machine_code.tolist(),key='equipment_master_edit_code')
        edit_row=EQUIPMENT[EQUIPMENT.machine_code==edit_code].iloc[0]
        with st.form(f'edit_equipment_master_form_{edit_code}'):
            e1,e2=st.columns(2); e1.text_input('Machine Code',value=edit_code,disabled=True); edit_name=e2.text_input('Machine Name *',value=str(edit_row.machine_name))
            e3,e4,e5=st.columns(3); edit_make=e3.text_input('Make / Model',value=str(edit_row.make_model)); edit_capacity=e4.text_input('Capacity',value=str(edit_row.capacity)); edit_location=e5.text_input('Location *',value=str(edit_row.location))
            edit_active=st.checkbox('Active',value=bool(edit_row.is_active)); update_machine=st.form_submit_button('💾 Save Machine Changes',type='primary')
        if update_machine:
            if not edit_name.strip() or not edit_location.strip():st.error('Machine Name और Location required हैं।')
            else:
                now=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(timespec='seconds'); execsql('update equipment_master set machine_name=?,make_model=?,capacity=?,location=?,is_active=?,updated_at=? where machine_code=?',(edit_name.strip(),edit_make.strip(),edit_capacity.strip(),edit_location.strip(),bool(edit_active),now,edit_code)); st.success(f'{edit_code} successfully update हो गई।'); st.rerun()
    st.info('Machine Code primary link है, इसलिए existing code edit नहीं किया जा सकता। Machine हटाने के बजाय Active checkbox off करें; उसकी पुरानी history सुरक्षित रहेगी।')
with T[9]:
    st.subheader('Machine → PM Checklist Mapping'); code=st.selectbox('Machine Code',MACH.machine_code.tolist(),key='mapcode'); mr=machine_row(code); current=checklist_for(code); opts=['NOT CONFIGURED']+list(CHECKS.keys()); idx=opts.index(current) if current in opts else 0; sel=st.selectbox('Checklist Template',opts,index=idx)
    if st.button('Save Mapping',type='primary'):
        if sel=='NOT CONFIGURED':execsql('delete from checklist_map where machine_code=?',(code,))
        else:execsql('insert or replace into checklist_map(machine_code,sheet_name) values(?,?)',(code,sel))
        st.success(f'Mapping saved: {mr.machine_name} → {sel}')
    st.caption('Missing machine checklists can be added later without rebuilding the dashboard. Map them here when available.')
