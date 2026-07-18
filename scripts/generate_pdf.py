#!/usr/bin/env python3
"""
Resume PDF Generator — generates tailored resume PDFs from LLM tailoring JSON.
Uses ReportLab for professional formatting with ATS-friendly plain text.

Usage:
  python3 generate_pdf.py output/tailoring_results_all.json
  python3 generate_pdf.py output/tailoring_humana_v4.json
"""

import json
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "resume" / "tailored"

# Contact info — plain text, no hyperlinks (ATS-friendly)
CONTACT_INFO = (
    'Westborough, MA &middot; '
    '(774) 244-9321 &middot; '
    'george@mishchenko.us &middot; '
    'mishchenko.us &middot; '
    'linkedin.com/in/george-mishchenko-46139910'
)

# Colors
DARK = HexColor('#2c3e50')
GRAY = HexColor('#7f8c8d')
LIGHT_GRAY = HexColor('#bdc3c7')
BODY_COLOR = HexColor('#333333')

# Styles
styles = getSampleStyleSheet()

name_style = ParagraphStyle('Name', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=16, textColor=DARK, spaceAfter=2, leading=20)

subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontName='Helvetica', fontSize=9, textColor=GRAY, spaceAfter=10, leading=12)

section_style = ParagraphStyle('Section', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=11, textColor=DARK,
    spaceBefore=6, spaceAfter=2, leading=14)

body_style = ParagraphStyle('Body', parent=styles['Normal'],
    fontName='Helvetica', fontSize=10.5, textColor=BODY_COLOR,
    leading=14)

job_header_style = ParagraphStyle('JobHeader', parent=styles['Normal'],
    fontName='Helvetica-Bold', fontSize=10.5, textColor=DARK,
    spaceBefore=4, spaceAfter=2, leading=14)

bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
    fontName='Helvetica', fontSize=10.5, textColor=BODY_COLOR,
    leftIndent=14, bulletIndent=2, leading=14, spaceAfter=1)

strength_style = ParagraphStyle('Strength', parent=styles['Normal'],
    fontName='Helvetica', fontSize=10.5, textColor=BODY_COLOR,
    leftIndent=10, bulletIndent=0, leading=14, spaceAfter=1)


def clean(text):
    """Clean text for ReportLab — replace problematic unicode."""
    return text.replace('\u2014', '\u2014').replace('\u2013', '\u2013').replace('\u2019', "'")


def generate_pdf(data, filepath):
    """Generate a single tailored resume PDF."""
    
    # Header content for repeating on every page
    header_name_style = ParagraphStyle('HeaderName', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, textColor=DARK, spaceAfter=1, leading=14)
    header_contact_style = ParagraphStyle('HeaderContact', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, textColor=GRAY, spaceAfter=2, leading=10)
    
    def header_footer(canvas, doc):
        canvas.saveState()
        # Header — same fonts as original first-page header
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(DARK)
        canvas.drawString(0.75*inch, 10.55*inch, 'George Mishchenko')
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(0.75*inch, 10.35*inch,
            'Westborough, MA  \u00b7  (774) 244-9321  \u00b7  george@mishchenko.us  \u00b7  linkedin.com/in/george-mishchenko-46139910')
        # Horizontal rule under header
        canvas.setStrokeColor(DARK)
        canvas.setLineWidth(2)
        canvas.line(0.75*inch, 10.25*inch, 7.75*inch, 10.25*inch)
        canvas.restoreState()
    
    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=1.05*inch, bottomMargin=0.6*inch)

    story = []

    # First page header (inline, not repeated — the canvas handles repeats)
    # Professional Summary
    story.append(Paragraph('PROFESSIONAL SUMMARY', section_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GRAY, spaceAfter=4))
    story.append(Paragraph(clean(data['tailored_summary']), body_style))

    # Core Strengths — two column
    story.append(Spacer(1, 3))
    story.append(Paragraph('CORE STRENGTHS', section_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GRAY, spaceAfter=4))

    strengths = data['tailored_strengths']
    mid = (len(strengths) + 1) // 2
    col1 = [Paragraph(f'\u2022 {clean(s)}', strength_style) for s in strengths[:mid]]
    col2 = [Paragraph(f'\u2022 {clean(s)}', strength_style) for s in strengths[mid:]]
    while len(col2) < len(col1):
        col2.append(Paragraph('', strength_style))
    col_data = list(zip(col1, col2))
    strength_table = Table(col_data, colWidths=[3.25*inch, 3.25*inch])
    strength_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(strength_table)

    # Career Highlights
    story.append(Spacer(1, 3))
    story.append(Paragraph('CAREER HIGHLIGHTS', section_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GRAY, spaceAfter=4))

    for entry in data['tailored_highlights']:
        story.append(Paragraph(clean(entry['header']), job_header_style))
        if entry.get('intro'):
            intro_style = ParagraphStyle('Intro', parent=body_style,
                fontName='Helvetica-Oblique', fontSize=9.5, textColor=GRAY, spaceAfter=3, leading=12)
            story.append(Paragraph(clean(entry['intro']), intro_style))
        bullet_items = [ListItem(Paragraph(clean(b), bullet_style), leftIndent=14, value='\u2013') for b in entry['bullets']]
        story.append(ListFlowable(bullet_items, bulletType='bullet', start='\u2013', leftIndent=6))
        story.append(Spacer(1, 4))

    # Education
    story.append(Spacer(1, 3))
    story.append(Paragraph('EDUCATION &amp; CERTIFICATIONS', section_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GRAY, spaceAfter=4))
    story.append(Paragraph('AIPMM Certified Product Manager, Master of Science in IT at Clark University', body_style))
    story.append(Paragraph('Bachelor of Science in Business Informatics at Southern Urals State University', body_style))

    # Tools (if present)
    tools = data.get('tailored_tools', {})
    if tools:
        story.append(Spacer(1, 3))
        story.append(Paragraph('TOOLS &amp; TECHNOLOGIES', section_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GRAY, spaceAfter=4))
        if isinstance(tools, dict):
            for category, items in tools.items():
                items_text = ', '.join(items) if isinstance(items, list) else str(items)
                story.append(Paragraph(f'<b>{category}:</b> {clean(items_text)}', body_style))
        elif isinstance(tools, list):
            for category_item in tools:
                story.append(Paragraph(clean(category_item), body_style))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_pdf.py <tailoring_json> [--skip-validation]")
        sys.exit(1)

    skip_validation = '--skip-validation' in sys.argv
    filepath_arg = sys.argv[1]

    with open(filepath_arg) as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    # Validate and auto-fix before generating PDFs
    if not skip_validation:
        from validate_tailoring import validate_entry, validate_and_fix
        fixed_count = 0
        error_count = 0
        for idx, entry in enumerate(data):
            entry, changes = validate_and_fix(entry)
            if changes:
                fixed_count += 1
            errors = validate_entry(entry, idx)
            if errors:
                error_count += 1
                for e in errors:
                    print(f"  ⚠ {e}")
        
        if fixed_count > 0:
            # Save fixed data
            with open(filepath_arg, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Auto-fixed: {fixed_count} entries (order/bad entries)")
        
        if error_count > 0:
            print(f"Validation warnings: {error_count} entries have issues (pandering, length, etc.)")
            print("PDFs will still be generated. Review warnings above.")
        else:
            print("Validation passed: all entries clean.")

    for item in data:
        company = item.get('company', 'Unknown')
        title = item.get('title', 'Role')
        
        # Gate 1: Technical quality check
        from quality_gate import score_entry
        qscore, qissues = score_entry(item)
        if qscore < 75:
            print(f'  ✗ REJECTED (technical): {company} ({qscore}/100) — skipped')
            for issue in qissues:
                print(f'    ⚠ {issue}')
            continue
        
        # Gate 2: Human review (LLM) — only if review JSON exists
        review_path = OUTPUT_DIR / f"{company}_review.json"
        if review_path.exists():
            with open(review_path) as rf:
                review = json.load(rf)
            hr_score = review.get('hr_score', 100)
            hm_score = review.get('hm_score', 100)
            if hr_score < 70 or hm_score < 70:
                print(f'  ✗ REJECTED (review): {company} HR={hr_score} HM={hm_score} — skipped')
                for issue in review.get('hr_issues', []):
                    print(f'    ⚠ HR: {issue}')
                for issue in review.get('hm_issues', []):
                    print(f'    ⚠ HM: {issue}')
                continue
            print(f'  ✓ {company} (tech={qscore} HR={hr_score} HM={hm_score})')
        else:
            print(f'  ~ {company} (tech={qscore}, no human review)')
        
        safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        outpath = OUTPUT_DIR / f"{safe_co}_{safe_ti}_2026-07-17.pdf"
        generate_pdf(item, outpath)
        print(f"    Generated: {outpath.name}")


if __name__ == "__main__":
    main()