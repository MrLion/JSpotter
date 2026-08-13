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

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "resume" / "tailored"

# Load config
def load_config():
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"candidate": {"name": "", "career_order": []}}

CONFIG = load_config()
CANDIDATE = CONFIG.get("candidate", {})
CANDIDATE_NAME = CANDIDATE.get("name", "")
CAREER_ORDER = CANDIDATE.get("career_order", [])

# Load theme
def load_theme():
    theme_path = BASE_DIR / "theme.json"
    if theme_path.exists():
        with open(theme_path) as f:
            return json.load(f)
    # Defaults
    return {
        "fonts": {
            "name": {"family": "Helvetica-Bold", "size": 16},
            "subtitle": {"family": "Helvetica", "size": 8},
            "section_header": {"family": "Helvetica-Bold", "size": 11},
            "job_header": {"family": "Helvetica-Bold", "size": 10.5},
            "body": {"family": "Helvetica", "size": 10.5},
            "bullet": {"family": "Helvetica", "size": 10.5},
            "intro": {"family": "Helvetica-Oblique", "size": 9.5}
        },
        "colors": {
            "name": "#2c3e50", "subtitle": "#7f8c8d", "section_header": "#2c3e50",
            "job_header": "#2c3e50", "body": "#333333", "intro": "#7f8c8d",
            "rule_primary": "#2c3e50", "rule_section": "#bdc3c7", "link": "#2563eb"
        },
        "layout": {
            "margin_left": 0.75, "margin_right": 0.75, "margin_top": 1.05, "margin_bottom": 0.6,
            "header_name_y": 10.55, "header_subtitle_y": 10.35, "header_rule_y": 10.25,
            "header_rule_width": 2, "section_rule_width": 0.5,
            "section_space_before": 6, "section_space_after": 2,
            "spacer_between_sections": 3, "spacer_between_jobs": 4
        },
        "strengths": {"columns": 2, "bullet_char": "\u2022"},
        "bullets": {"char": "\u2013", "indent": 14, "max_words": 25},
        "education": [],
        "contact_info": {
            "line1": "", "line2": ""
        }
    }

THEME = load_theme()
T_FONTS = THEME["fonts"]
T_COLORS = THEME["colors"]
T_LAYOUT = THEME["layout"]
T_STRENGTHS = THEME["strengths"]
T_BULLETS = THEME["bullets"]
T_CONTACT = THEME["contact_info"]

# Colors from theme
DARK = HexColor(T_COLORS["name"])
GRAY = HexColor(T_COLORS["subtitle"])
LIGHT_GRAY = HexColor(T_COLORS["rule_section"])
BODY_COLOR = HexColor(T_COLORS["body"])

# Styles from theme
styles = getSampleStyleSheet()

name_style = ParagraphStyle('Name', parent=styles['Normal'],
    fontName=T_FONTS["name"]["family"], fontSize=T_FONTS["name"]["size"], textColor=DARK, spaceAfter=2, leading=T_FONTS["name"]["size"] + 4)

subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontName=T_FONTS["subtitle"]["family"], fontSize=T_FONTS["subtitle"]["size"], textColor=GRAY, spaceAfter=10, leading=T_FONTS["subtitle"]["size"] + 3)

section_style = ParagraphStyle('Section', parent=styles['Normal'],
    fontName=T_FONTS["section_header"]["family"], fontSize=T_FONTS["section_header"]["size"], textColor=HexColor(T_COLORS["section_header"]),
    spaceBefore=T_LAYOUT["section_space_before"], spaceAfter=T_LAYOUT["section_space_after"], leading=T_FONTS["section_header"]["size"] + 3)

body_style = ParagraphStyle('Body', parent=styles['Normal'],
    fontName=T_FONTS["body"]["family"], fontSize=T_FONTS["body"]["size"], textColor=BODY_COLOR,
    leading=T_FONTS["body"]["size"] + 3)

job_header_style = ParagraphStyle('JobHeader', parent=styles['Normal'],
    fontName=T_FONTS["job_header"]["family"], fontSize=T_FONTS["job_header"]["size"], textColor=HexColor(T_COLORS["job_header"]),
    spaceBefore=4, spaceAfter=2, leading=T_FONTS["job_header"]["size"] + 3)

bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
    fontName=T_FONTS["bullet"]["family"], fontSize=T_FONTS["bullet"]["size"], textColor=BODY_COLOR,
    leftIndent=T_BULLETS["indent"], bulletIndent=2, leading=T_FONTS["bullet"]["size"] + 3, spaceAfter=1)

strength_style = ParagraphStyle('Strength', parent=styles['Normal'],
    fontName=T_FONTS["bullet"]["family"], fontSize=T_FONTS["bullet"]["size"], textColor=BODY_COLOR,
    leftIndent=10, bulletIndent=0, leading=T_FONTS["bullet"]["size"] + 3, spaceAfter=1)


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
    
    def header_first(canvas, doc):
        """Full header on first page — name, contact info, rule."""
        canvas.saveState()
        name_font = T_FONTS["name"]
        sub_font = T_FONTS["subtitle"]
        canvas.setFont(name_font["family"], name_font["size"])
        canvas.setFillColor(HexColor(T_COLORS["name"]))
        canvas.drawString(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_name_y"]*inch, CANDIDATE_NAME)
        canvas.setFont(sub_font["family"], sub_font["size"])
        canvas.setFillColor(HexColor(T_COLORS["subtitle"]))
        contact_line = T_CONTACT.get("line1", "")
        if T_CONTACT.get("line2"):
            contact_line = contact_line + "  \u00b7  " + T_CONTACT["line2"] if contact_line else T_CONTACT["line2"]
        canvas.drawString(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_subtitle_y"]*inch, contact_line)
        canvas.setStrokeColor(HexColor(T_COLORS["rule_primary"]))
        canvas.setLineWidth(T_LAYOUT["header_rule_width"])
        right_edge = (8.5 - T_LAYOUT["margin_right"]) * inch
        canvas.line(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_rule_y"]*inch, right_edge, T_LAYOUT["header_rule_y"]*inch)
        canvas.restoreState()

    def header_later(canvas, doc):
        """Minimal header on page 2+ — just name, no contact info. Saves space and avoids ATS confusion."""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(HexColor(T_COLORS["subtitle"]))
        canvas.drawString(T_LAYOUT["margin_left"]*inch, 10.55*inch, CANDIDATE_NAME)
        canvas.setStrokeColor(HexColor(T_COLORS["rule_section"]))
        canvas.setLineWidth(T_LAYOUT["section_rule_width"])
        right_edge = (8.5 - T_LAYOUT["margin_right"]) * inch
        canvas.line(T_LAYOUT["margin_left"]*inch, 10.45*inch, right_edge, 10.45*inch)
        canvas.restoreState()
    
    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
        leftMargin=T_LAYOUT["margin_left"]*inch, rightMargin=T_LAYOUT["margin_right"]*inch,
        topMargin=T_LAYOUT["margin_top"]*inch, bottomMargin=T_LAYOUT["margin_bottom"]*inch)

    story = []

    # First page header (inline, not repeated — the canvas handles repeats)
    # Professional Summary
    story.append(Paragraph('PROFESSIONAL SUMMARY', section_style))
    story.append(HRFlowable(width='100%', thickness=T_LAYOUT["section_rule_width"], color=LIGHT_GRAY, spaceAfter=4))
    story.append(Paragraph(clean(data['tailored_summary']), body_style))

    # Core Strengths — two column
    story.append(Spacer(1, T_LAYOUT["spacer_between_sections"]))
    story.append(Paragraph('CORE STRENGTHS', section_style))
    story.append(HRFlowable(width='100%', thickness=T_LAYOUT["section_rule_width"], color=LIGHT_GRAY, spaceAfter=4))

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
    story.append(Spacer(1, T_LAYOUT["spacer_between_sections"]))
    story.append(Paragraph('CAREER HIGHLIGHTS', section_style))
    story.append(HRFlowable(width='100%', thickness=T_LAYOUT["section_rule_width"], color=LIGHT_GRAY, spaceAfter=4))

    for entry in data['tailored_highlights']:
        header = clean(entry['header'])
        # Add date range if missing — from config career_order
        has_date = any(c.isdigit() for c in header[-12:])
        if not has_date and CAREER_ORDER:
            for career_entry in CAREER_ORDER:
                if any(kw.lower() in header.lower() for kw in career_entry.get("keywords", [])):
                    header = f"{header} {career_entry['dates']}"
                    break
        story.append(Paragraph(header, job_header_style))
        if entry.get('intro'):
            intro_style = ParagraphStyle('Intro', parent=body_style,
                fontName='Helvetica-Oblique', fontSize=9.5, textColor=GRAY, spaceAfter=3, leading=12)
            story.append(Paragraph(clean(entry['intro']), intro_style))
        bullet_items = [ListItem(Paragraph(clean(b), bullet_style), leftIndent=14, value='\u2013') for b in entry['bullets']]
        story.append(ListFlowable(bullet_items, bulletType='bullet', start='\u2013', leftIndent=6))
        story.append(Spacer(1, T_LAYOUT["spacer_between_jobs"]))

    # Education — read from theme.json
    story.append(Spacer(1, T_LAYOUT["spacer_between_sections"]))
    story.append(Paragraph('EDUCATION &amp; CERTIFICATIONS', section_style))
    story.append(HRFlowable(width='100%', thickness=T_LAYOUT["section_rule_width"], color=LIGHT_GRAY, spaceAfter=4))
    for edu in THEME.get("education", []):
        story.append(Paragraph(clean(edu["text"]), body_style))

    # Tools (if present)
    tools = data.get('tailored_tools', {})
    if tools:
        story.append(Spacer(1, T_LAYOUT["spacer_between_sections"]))
        story.append(Paragraph('TOOLS &amp; TECHNOLOGIES', section_style))
        story.append(HRFlowable(width='100%', thickness=T_LAYOUT["section_rule_width"], color=LIGHT_GRAY, spaceAfter=4))
        if isinstance(tools, dict):
            for category, items in tools.items():
                items_text = ', '.join(items) if isinstance(items, list) else str(items)
                story.append(Paragraph(f'<b>{category}:</b> {clean(items_text)}', body_style))
        elif isinstance(tools, list):
            for item in tools:
                # Handle "**Category:** items" format from subagents
                if item.startswith('**') and ':**' in item:
                    cat_end = item.index(':**')
                    category = item[2:cat_end]
                    items_text = item[cat_end+3:].strip()
                    story.append(Paragraph(f'<b>{category}:</b> {clean(items_text)}', body_style))
                else:
                    story.append(Paragraph(clean(item), body_style))

    # Adjust top margin — page 2+ uses smaller header
    doc.build(story, onFirstPage=header_first, onLaterPages=header_later)


def generate_cover_letter_pdf(data, filepath):
    """Generate a cover letter PDF following standard business letter format."""
    from datetime import datetime
    
    def cl_header(canvas, doc):
        """Same header as resume page 1."""
        canvas.saveState()
        name_font = T_FONTS["name"]
        sub_font = T_FONTS["subtitle"]
        canvas.setFont(name_font["family"], name_font["size"])
        canvas.setFillColor(HexColor(T_COLORS["name"]))
        canvas.drawString(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_name_y"]*inch, CANDIDATE_NAME)
        canvas.setFont(sub_font["family"], sub_font["size"])
        canvas.setFillColor(HexColor(T_COLORS["subtitle"]))
        contact_line = T_CONTACT.get("line1", "")
        if T_CONTACT.get("line2"):
            contact_line = contact_line + "  \u00b7  " + T_CONTACT["line2"] if contact_line else T_CONTACT["line2"]
        canvas.drawString(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_subtitle_y"]*inch, contact_line)
        canvas.setStrokeColor(HexColor(T_COLORS["rule_primary"]))
        canvas.setLineWidth(T_LAYOUT["header_rule_width"])
        right_edge = (8.5 - T_LAYOUT["margin_right"]) * inch
        canvas.line(T_LAYOUT["margin_left"]*inch, T_LAYOUT["header_rule_y"]*inch, right_edge, T_LAYOUT["header_rule_y"]*inch)
        canvas.restoreState()
    
    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
        leftMargin=T_LAYOUT["margin_left"]*inch, rightMargin=T_LAYOUT["margin_right"]*inch,
        topMargin=T_LAYOUT["margin_top"]*inch, bottomMargin=T_LAYOUT["margin_bottom"]*inch)
    
    company = data.get('company', '')
    title = data.get('title', '')
    today = datetime.now().strftime('%B %d, %Y')
    
    story = []
    
    # 1. Date
    story.append(Paragraph(today, body_style))
    story.append(Spacer(1, 12))
    
    # 2. Recipient/company address block
    story.append(Paragraph(f'Hiring Manager', body_style))
    story.append(Paragraph(f'{company}', body_style))
    story.append(Paragraph(f'Re: Application for {title}', body_style))
    story.append(Spacer(1, 12))
    
    # 4. Body paragraphs (split cover letter, strip greeting and any closing)
    cover_text = data.get('cover_letter', '')
    paragraphs = cover_text.replace('\\n', '\n').split('\n\n')
    
    # Extract salutation if present
    salutation = ''
    body_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_lower = para.lower()
        # Salutation — keep
        if para_lower.startswith('dear ') or para_lower.startswith('to '):
            salutation = para
            continue
        # Any closing line — strip (generator adds standard business closing)
        if any(phrase in para_lower for phrase in ['regards', 'sincerely', 'best regards', 'best,', 'thank you for', 'respectfully']):
            continue
        # Name/contact lines — strip (generator adds standard business closing)
        if CANDIDATE_NAME.lower() in para_lower or ('mishchenko' in para_lower and not para.endswith('.')):
            continue
        body_paragraphs.append(para)
    
    # Salutation
    if salutation:
        story.append(Paragraph(clean(salutation), body_style))
        story.append(Spacer(1, 8))
    else:
        story.append(Paragraph('Dear Hiring Manager,', body_style))
        story.append(Spacer(1, 8))
    
    # Body
    for para in body_paragraphs:
        story.append(Paragraph(clean(para), body_style))
        story.append(Spacer(1, 8))
    
    # 5. Standard business closing — always render this
    story.append(Spacer(1, 4))
    story.append(Paragraph('Sincerely,', body_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(CANDIDATE_NAME, body_style))
    
    # 6. Enclosure notation
    story.append(Spacer(1, 12))
    story.append(Paragraph('<i>Enclosure: Resume</i>', body_style))
    
    doc.build(story, onFirstPage=cl_header, onLaterPages=cl_header)


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
        
        # Gate 2: Human review (LLM) — informational, generates review notes
        # Try multiple review file naming patterns (company, company+title)
        safe_co_review = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        safe_ti_review = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        review_path = OUTPUT_DIR / f"{company}_review.json"
        if not review_path.exists():
            review_path = OUTPUT_DIR / f"{safe_co_review}_review.json"
        if not review_path.exists():
            review_path = OUTPUT_DIR / f"{safe_co_review} {safe_ti_review}_review.json"
        if not review_path.exists():
            review_path = OUTPUT_DIR / f"{safe_co_review}_{safe_ti_review}_review.json"
        if review_path.exists():
            with open(review_path) as rf:
                review = json.load(rf)
            
            # Handle both flat and nested JSON structures
            hr_score = review.get('hr_score')
            hm_score = review.get('hm_score')
            hr_notes = review.get('hr_notes', '')
            hm_notes = review.get('hm_notes', '')
            hr_issues = review.get('hr_issues', [])
            hm_issues = review.get('hm_issues', [])
            hm_questions = review.get('hm_interview_questions', [])
            
            if hr_score is None and 'hr_recruiter_review' in review:
                hr_data = review['hr_recruiter_review']
                hr_score = hr_data.get('total_score', hr_data.get('score_100', 100))
                hr_issues = hr_data.get('issues', [])
                hr_notes = hr_data.get('notes', '')
                if isinstance(hr_notes, dict):
                    hr_notes = hr_notes.get('notes', str(hr_notes))
            
            if hm_score is None and 'hiring_manager_review' in review:
                hm_data = review['hiring_manager_review']
                hm_score = hm_data.get('total_score', hm_data.get('score_100', 100))
                hm_issues = hm_data.get('issues', [])
                hm_notes = hm_data.get('notes', '')
                if isinstance(hm_notes, dict):
                    hm_notes = hm_notes.get('notes', str(hm_notes))
                hm_questions = hm_data.get('interview_questions', [])
            
            hr_score = hr_score or 100
            hm_score = hm_score or 100
            status = review.get('status', 'PASS')
            if status == 'PASS' and 'overall' in review:
                overall = review['overall']
                if isinstance(overall, dict):
                    status = overall.get('status', 'PASS')
            
            # Write review notes alongside the PDF
            safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
            safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            notes_path = OUTPUT_DIR / f"{safe_co}_{safe_ti}_review_notes.txt"
            notes = f"QUALITY REVIEW: {company} — {title}\n"
            notes += f"{'='*60}\n\n"
            notes += f"HR Score: {hr_score}/100\n"
            notes += f"HM Score: {hm_score}/100\n"
            notes += f"Status: {status}\n\n"
            notes += f"HR Notes: {hr_notes}\n"
            notes += f"HM Notes: {hm_notes}\n\n"
            notes += "HR Issues:\n"
            for issue in hr_issues:
                notes += f"  - {issue}\n"
            notes += "\nHM Issues:\n"
            for issue in hm_issues:
                notes += f"  - {issue}\n"
            notes += "\nHM Interview Questions:\n"
            for q in hm_questions:
                notes += f"  ? {q}\n"
            if status == 'FAIL' or hr_score < 70 or hm_score < 70:
                notes += f"\nRegenerate Feedback: {review.get('regenerate_feedback', '')}\n"
            notes_path.write_text(notes)
            
            # Clean up JSON review file — only keep txt notes
            review_path.unlink()
            
            if hr_score < 70 or hm_score < 70:
                print(f'  ⚠ {company} (tech={qscore} HR={hr_score} HM={hm_score}) — review below threshold, PDF generated with notes')
            else:
                print(f'  ✓ {company} (tech={qscore} HR={hr_score} HM={hm_score})')
        
        # Extract version from input filename (e.g. tailoring_athenahealth_v2.json → v2)
        import re
        input_name = Path(filepath_arg).stem
        version_match = re.search(r'(_v\d+)$', input_name)
        version_suffix = version_match.group(1) if version_match else ''
        
        safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        safe_name = "".join(c for c in CANDIDATE_NAME if c.isalnum() or c in " -_").strip()
        outpath = OUTPUT_DIR / f"{safe_name}_{safe_co}_{safe_ti}{version_suffix}.pdf"
        generate_pdf(item, outpath)
        # Save cover letter as PDF
        cover = item.get('cover_letter', '')
        if cover:
            cl_path = OUTPUT_DIR / f"{safe_name}_{safe_co}_{safe_ti}{version_suffix}_cover_letter.pdf"
            generate_cover_letter_pdf(item, cl_path)
            print(f"    Generated: {outpath.name} + cover letter PDF")
        else:
            print(f"    Generated: {outpath.name}")


if __name__ == "__main__":
    main()