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

runtime_globals={'__name__':'__main__','__file__':str(DASHBOARD_SCRIPT),'__package__':None,'__cached__':None}
exec(compile(source,str(DASHBOARD_SCRIPT),'exec'),runtime_globals)
