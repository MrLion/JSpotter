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
        review_path = OUTPUT_DIR / f"{company}_review.json"
        if review_path.exists():
            with open(review_path) as rf:
                review = json.load(rf)
            hr_score = review.get('hr_score', 100)
            hm_score = review.get('hm_score', 100)
            status = review.get('status', 'PASS')
            
            # Write review notes alongside the PDF
            safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
            safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
            notes_path = OUTPUT_DIR / f"{safe_co}_{safe_ti}_review_notes.txt"
            notes = f"QUALITY REVIEW: {company} — {title}\n"
            notes += f"{'='*60}\n\n"
            notes += f"HR Score: {hr_score}/100\n"
            notes += f"HM Score: {hm_score}/100\n"
            notes += f"Status: {status}\n\n"
            notes += f"HR Notes: {review.get('hr_notes', '')}\n"
            notes += f"HM Notes: {review.get('hm_notes', '')}\n\n"
            notes += "HR Issues:\n"
            for issue in review.get('hr_issues', []):
                notes += f"  - {issue}\n"
            notes += "\nHM Issues:\n"
            for issue in review.get('hm_issues', []):
                notes += f"  - {issue}\n"
            notes += "\nHM Interview Questions:\n"
            for q in review.get('hm_interview_questions', []):
                notes += f"  ? {q}\n"
            if status == 'FAIL':
                notes += f"\nRegenerate Feedback: {review.get('regenerate_feedback', '')}\n"
            notes_path.write_text(notes)
            
            if hr_score < 70 or hm_score < 70:
                print(f'  ⚠ {company} (tech={qscore} HR={hr_score} HM={hm_score}) — review below threshold, PDF generated with notes')
            else:
                print(f'  ✓ {company} (tech={qscore} HR={hr_score} HM={hm_score})')
        
        safe_co = "".join(c for c in company if c.isalnum() or c in " -_").strip()
        safe_ti = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        outpath = OUTPUT_DIR / f"{safe_co}_{safe_ti}_2026-07-17.pdf"
        generate_pdf(item, outpath)
        print(f"    Generated: {outpath.name}")


if __name__ == "__main__":
    main()