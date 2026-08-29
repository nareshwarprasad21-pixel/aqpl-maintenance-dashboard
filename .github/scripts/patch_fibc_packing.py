from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old_cache = "STATIC_MACH,PLAN,CHECKS=load_static('2026-08-25-pneumatic-line-v1')"
new_cache = "STATIC_MACH,PLAN,CHECKS=load_static('2026-08-29-packing-machine-v1')"
if old_cache in text:
    text = text.replace(old_cache, new_cache, 1)
elif new_cache not in text:
    raise SystemExit('Expected load_static cache-version line not found')

old_override = "    if code=='AQPL/P LINE':return 'PNEUMATIC CONVEYING LINE'\n"
new_override = (
    "    if code=='AQPL/P LINE':return 'PNEUMATIC CONVEYING LINE'\n"
    "    if code=='AQPL/FIBC-A':return 'PACKING MACHINE'\n"
)
if "if code=='AQPL/FIBC-A':return 'PACKING MACHINE'" not in text:
    if old_override not in text:
        raise SystemExit('Expected checklist_for override anchor not found')
    text = text.replace(old_override, new_override, 1)

path.write_text(text, encoding='utf-8')
print('FIBC packing checklist cache + mapping override patched successfully')
