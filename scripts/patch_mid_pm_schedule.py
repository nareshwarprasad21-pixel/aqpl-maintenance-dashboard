from pathlib import Path
import csv
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
MACHINES = ROOT / 'data' / 'machines.csv'
PLAN = ROOT / 'data' / 'pm_plan.csv'

# New MID-section equipment requested by user.
# H-5A is added to the machine master, but the uploaded 2026-27 PM plan does not
# contain a row/date series for H-5A, so no schedule is invented for it.
new_machines = [
    ('MID BELT CONVEYOR BC-1','AQPL/MID BC-1','','','MID'),
    ('MID BELT CONVEYOR BC-2','AQPL/MID BC-2','','','MID'),
    ('MID BELT CONVEYOR BC-3','AQPL/MID BC-3','','','MID'),
    ('MID HOPPER / CONVEYOR H-1','AQPL/MID BC H-1','','','MID'),
    ('MID HOPPER / CONVEYOR H-8','AQPL/MID BC H-8','','','MID'),
    ('MID HOPPER / CONVEYOR H-6','AQPL/MID BC H-6','','','MID'),
    ('MID BELT CONVEYOR BC-4','AQPL/MID BC-4','','','MID'),
    ('MID HOPPER / CONVEYOR H-5','AQPL/MID BC H-5','','','MID'),
    ('MID HOPPER / CONVEYOR H-5A','AQPL/MID BC H-5A','','','MID'),
    ('MID HOPPER / CONVEYOR H-4','AQPL/MID H-4','','','MID'),
    ('MID HOPPER / CONVEYOR H-4A','AQPL/MID BC H-4A','','','MID'),
    ('MID WEIGH FEEDER WF-1','AQPL/MID WF-1','','','MID'),
    ('MID WEIGH FEEDER WF-2','AQPL/MID WF-2','','','MID'),
    ('MID WEIGH FEEDER WF-3','AQPL/MID WF-3','','','MID'),
]

# Exact monthly dates from the uploaded preventive-maintenance plan.
# Each list is Apr-2026 through Mar-2027.
schedule_days = {
    'AQPL/MID BC H-1': 14,
    'AQPL/MID BC H-8': 17,
    'AQPL/MID WF-1': 18,
    'AQPL/MID WF-2': 19,
    'AQPL/MID WF-3': 20,
    'AQPL/MID BC H-6': 21,
    'AQPL/MID BC-4': 22,
    'AQPL/MID H-4': 6,
    'AQPL/MID BC H-4A': 7,
    'AQPL/MID BC-1': 11,
    'AQPL/MID BC-2': 12,
    'AQPL/MID BC-3': 13,
    'AQPL/MID BC H-5': 8,
}
name_by_code = {code:name for name,code,_,_,_ in new_machines}

# Append missing machines without changing any existing machine data.
with MACHINES.open(newline='', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
existing_codes = {r['machine_code'].strip() for r in rows}
for name, code, make, capacity, location in new_machines:
    if code not in existing_codes:
        rows.append({'machine_name':name,'machine_code':code,'make_model':make,'capacity':capacity,'location':location})
        existing_codes.add(code)
with MACHINES.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['machine_name','machine_code','make_model','capacity','location'])
    w.writeheader(); w.writerows(rows)

# Append/replace only the newly supplied MID schedule rows.
with PLAN.open(newline='', encoding='utf-8-sig') as f:
    plan_rows = list(csv.DictReader(f))
new_codes = set(schedule_days)
plan_rows = [r for r in plan_rows if r['machine_code'].strip() not in new_codes]
months = [(2026,m) for m in range(4,13)] + [(2027,m) for m in range(1,4)]
for code, day in schedule_days.items():
    for year, month in months:
        d = date(year, month, day)
        plan_rows.append({
            'machine_name': name_by_code[code],
            'machine_code': code,
            'frequency': '1 month',
            'scheduled_date': d.isoformat(),
        })
plan_rows.sort(key=lambda r: (r['scheduled_date'], r['machine_code']))
with PLAN.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['machine_name','machine_code','frequency','scheduled_date'])
    w.writeheader(); w.writerows(plan_rows)

print(f'Updated machine master with {len(new_machines)} MID machines.')
print(f'Updated PM plan for {len(schedule_days)} source-supported MID machines; H-5A schedule left pending because no source row was provided.')
