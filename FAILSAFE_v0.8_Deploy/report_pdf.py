"""Downloadable, synthetic-only outpatient analysis PDF for FAILSAFE.

The PDF is generated from the same validated simulation result shown online.
It contains no patient records, diagnostics or clinical recommendations.
"""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, Flowable,
)

FOREST = colors.HexColor('#244C36')
MOSS = colors.HexColor('#4D8062')
MUTED = colors.HexColor('#63756A')
IVORY = colors.HexColor('#F3F7F1')
SOFT = colors.HexColor('#E1EAE1')
AMBER = colors.HexColor('#A86A3C')
PAGE = A4


def _txt(value):
    return escape(str(value))


class CompletionBar(Flowable):
    """Two comparable completion bars using an honest shared 0%-100% scale."""
    def __init__(self, baseline, improved, width=500):
        super().__init__()
        self.b = baseline
        self.o = improved
        self.width = width
        self.height = 86

    def draw(self):
        can = self.canv
        for i, (label, value, color) in enumerate((('Current clinic', self.b, AMBER), ('Tested improvement', self.o, MOSS))):
            top = self.height - i * 42 - 16
            can.setFont('Helvetica', 9)
            can.setFillColor(FOREST)
            can.drawString(0, top, label)
            can.setFont('Helvetica-Bold', 9)
            can.drawRightString(self.width, top, f'{value:.1f}%')
            can.setFillColor(SOFT)
            can.roundRect(0, top-18, self.width, 10, 5, stroke=0, fill=1)
            can.setFillColor(color)
            can.roundRect(0, top-18, max(0, self.width * min(100, value)/100), 10, 5, stroke=0, fill=1)


def make_report_pdf(result: dict) -> bytes:
    """Generate a formatted PDF from a validated `outpatient.analyze` response."""
    buffer=BytesIO()
    doc=SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=45, leftMargin=45,
        topMargin=48, bottomMargin=44,
        title='FAILSAFE | Outpatient clinic performance report',
        author='FAILSAFE simulation prototype',
        subject='Illustrative outpatient workflow analysis; synthetic data only',
        pageCompression=1,
    )
    usable_width=A4[0]-90
    styles=getSampleStyleSheet()
    title=ParagraphStyle('FS-title',parent=styles['Heading1'],fontName='Helvetica-Bold',fontSize=22,leading=27,textColor=FOREST,spaceAfter=4)
    h2=ParagraphStyle('FS-h2',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=FOREST,spaceBefore=9,spaceAfter=5)
    body=ParagraphStyle('FS-body',parent=styles['BodyText'],fontName='Helvetica',fontSize=9.1,leading=12.8,textColor=FOREST,spaceAfter=5)
    muted=ParagraphStyle('FS-muted',parent=body,textColor=MUTED,fontSize=8.0,leading=11)
    eyebrow=ParagraphStyle('FS-eyebrow',parent=body,fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=MOSS,spaceAfter=10)
    small_bold=ParagraphStyle('FS-label',parent=body,fontName='Helvetica-Bold',fontSize=8.3,leading=12,spaceAfter=2)
    num=ParagraphStyle('FS-num',parent=body,fontName='Helvetica-Bold',fontSize=17,leading=21,spaceAfter=0)
    story=[]
    base=result['baseline']
    after=result['optimized']
    rec=result['recommendation']
    n=base['patients']
    gain=rec['added_completed']
    budget=result['scenario']['budget']
    story.append(Paragraph('FAILSAFE  /  OUTPATIENT CLINIC REPORT',eyebrow))
    story.append(Paragraph('Your clinic performance report',title))
    story.append(Paragraph('One fictional working day | Results based on the scenario entered in FAILSAFE.',muted))
    story.append(Spacer(1,6))

    table_data=[
        [Paragraph('COMPLETED BEFORE CLOSING',small_bold),Paragraph('AVERAGE MODELED WAIT',small_bold),Paragraph('NOT COMPLETED ON TIME',small_bold)],
        [Paragraph(f'{base["completed_before_close"]} / {n}',num),Paragraph(f'{base["average_wait_minutes"]} min' if base['average_wait_minutes'] is not None else '—',num),Paragraph(str(base['not_completed']),num)],
    ]
    t=Table(table_data,colWidths=[usable_width/3]*3)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),IVORY),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,0),10),('BOTTOMPADDING',(0,0),(-1,0),2),
        ('TOPPADDING',(0,1),(-1,1),1),('BOTTOMPADDING',(0,1),(-1,1),10),
        ('LINEBEFORE',(1,0),(-1,-1),0.6,SOFT),
    ]))
    story.append(t)
    story.append(Paragraph('Before vs. after: visits completed on time',h2))
    story.append(CompletionBar(base['completed_percent'],after['completed_percent'],usable_width))
    story.append(Paragraph(f'<b>{gain:+d} additional visits</b> completed before closing in this fictional scenario. '
                           f'The chosen option costs <b>EUR {rec["estimated_cost_eur"]:,.0f}</b> '
                           f'of the illustrative EUR {budget:,.0f} budget.',body))

    story.append(Paragraph('Potential bottlenecks',h2))
    top_findings=result['findings'][:4]
    for f in top_findings:
        title_text=_txt(f['title'])
        detail=_txt(f['detail'])
        story.append(Paragraph(f'<b>{title_text}</b> — {detail}',body))

    story.append(Paragraph('Suggested improvement and why',h2))
    acts=rec['actions']
    story.append(Paragraph('<b>' + (' + '.join(_txt(a) for a in acts) if acts else 'Keep the current configuration') + '</b>',body))
    story.append(Paragraph(_txt(rec['why_selected']),body))
    story.append(Paragraph('Ranking rule: (1) visits completed before closing, (2) average modeled waiting time, '
                           '(3) lower assumed cost. The system does not simply pick the longest queue.',muted))
    alt=rec.get('reception_alternative')
    if alt:
        story.append(Paragraph(
            f'A reception-staffing option also tested in this budget completed '
            f'<b>{alt["completed"]} / {n}</b> visits before closing '
            f'at an illustrative cost of <b>EUR {alt["cost_eur"]:,.0f}</b>. '
            f'The selected option completed <b>{after["completed_before_close"]} / {n}</b>.', muted))

    story.append(Paragraph('Scenario at a glance',h2))
    cfg=result['scenario']
    summary=[
        ('Patient visits', f'{n}'),
        ('Operating hours', f'{cfg["hours"]} h'),
        ('General / specialist clinicians', f'{cfg["general_doctors"]} / {cfg["specialist_doctors"]}'),
        ('Reception staff / nurses', f'{cfg["receptionists"]} / {cfg["nurses"]}'),
        ('Consultation / diagnostic rooms',f'{cfg["consult_rooms"]} / {cfg["diagnostic_rooms"]}'),
        ('Parking available',str(base['parking_spaces_available'])),
    ]
    rows=[]
    for i in range(0,len(summary),2):
        (lab1,val1),(lab2,val2)=summary[i:i+2]
        rows.append([Paragraph(f'<b>{_txt(lab1)}</b>  {_txt(val1)}',muted),
                     Paragraph(f'<b>{_txt(lab2)}</b>  {_txt(val2)}',muted)])
    tbl=Table(rows,colWidths=[usable_width/2]*2)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),IVORY),('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),11),
        ('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(tbl)

    story.append(Paragraph('Assumptions and limitations',h2))
    short_limits = [
        'Synthetic day only: visit types, arrival patterns, service times and costs are illustrative, not measured hospital data.',
        'Staff share opening hours; breaks, individual specialties, urgency, no-shows and clinical safety are not modeled.',
        'Parking is capacity-limited; optimization tests at most two changes and is not clinically validated.',
    ]
    for statement in short_limits:
        story.append(Paragraph('•  '+_txt(statement),muted))
    story.append(Spacer(1,4))
    story.append(Paragraph('<b>Important:</b> All data and costs are illustrative. This is a synthetic '
                           'hackathon demonstration, not a medical prediction, validated hospital model, '
                           'or clinical decision-support system.',muted))

    def footer(canvas, document):
        canvas.saveState()
        w,h=PAGE
        canvas.setStrokeColor(SOFT)
        canvas.line(45,39,w-45,39)
        canvas.setFillColor(MUTED)
        canvas.setFont('Helvetica',8)
        canvas.drawString(45,27,'FAILSAFE  ·  Synthetic healthcare workflow simulation')
        canvas.drawRightString(w-45,27,f'Page {document.page}')
        canvas.restoreState()

    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    pdf=buffer.getvalue()
    if not pdf.startswith(b'%PDF-'):
        raise ValueError('Unable to generate PDF')
    return pdf
