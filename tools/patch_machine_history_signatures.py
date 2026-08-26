from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
old = """    story.append(history_table)\n    def footer(canvas,document):\n"""
new = """    story.extend([history_table,Spacer(1,6*mm)])\n\n    # Match the approved AQPL Machine History Card format: keep clear\n    # Prepared By / Approved By signature boxes at the bottom of the report.\n    signatures=[\n        [Paragraph('<b>Prepared By</b>',body_bold),Paragraph('<b>Approved By</b>',body_bold)],\n        [Paragraph('<br/><br/>Name &amp; Signature: ______________________________',body),\n         Paragraph('<br/><br/>Name &amp; Signature: ______________________________',body)],\n        [Paragraph('Date: ____________________',body),Paragraph('Date: ____________________',body)]\n    ]\n    sign_table=Table(signatures,colWidths=[138.5*mm,138.5*mm])\n    sign_table.setStyle(TableStyle([\n        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#64748b')),\n        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2e8f0')),\n        ('VALIGN',(0,0),(-1,-1),'TOP'),\n        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),\n        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)\n    ]))\n    story.append(sign_table)\n\n    def footer(canvas,document):\n"""
if old not in text:
    raise SystemExit('Target Machine History PDF block not found')
path.write_text(text.replace(old,new,1),encoding='utf-8')
print('Machine History Prepared By / Approved By signature section added.')
