# ASIAN QUARTZ PVT LTD — Maintenance Management Dashboard V1

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Implemented linked workflow
- Machine Master (65 machine codes from AQPL master list)
- PM Plan (2026–27 scheduled dates)
- 35 PM checklist templates from `Preventive Check Sheet-JUNE26.xlsx`
- Machine → checklist mapping with `Not Configured` state
- PM job → PM checklist → Machine History → permit drafts when applicable
- BM job → Machine History → Breakdown History → permit drafts → Why-Why draft
- Height Work and Hot Work permit tracking based on AQPL FM-16 / FM-17 structure
- Why-Why / 5-Why RCA module (temporary standard format until AQPL official format is supplied)
- SQLite persistence in `data/maintenance.db`

## Next phase
- Exact printable Excel/PDF replicas of AQPL forms
- Exact legacy Machine Breakdown Slip mapping (old .xls)
- User login/roles, approvals/signatures
- Email/WhatsApp/notification layer for due PM
- Spare inventory, MTBF/MTTR, cost and downtime analytics
