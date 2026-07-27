#!/usr/bin/env python3
"""
Job Journal — Excel-based application & resume tracking spreadsheet.

Creates and maintains an .xlsx journal with sheets for:
  1. Jobs — all discovered jobs with scoring fields
  2. Applications — tracking pipeline (applied, interview, offer, rejected)
  3. Resume Versions — tailored resume tracking per job

Usage:
  python3 journal.py --init                           # create empty journal
  python3 journal.py --add output/linkedin_extract.json  # add jobs from JSON
  python3 journal.py --add output/linkedin_extract.json --mode append  # append to existing
  python3 journal.py --status                          # show summary stats
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
except ImportError:
    print("Error: openpyxl not installed. Run: pip3 install openpyxl")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
JOURNAL_PATH = BASE_DIR / "journal.xlsx"

# ─── Column definitions ───

JOBS_COLUMNS = [
    ("date_found", "Date Found", 12),
    ("company", "Company", 22),
    ("title", "Job Title", 35),
    ("location", "Location", 22),
    ("search_mode", "Source", 10),
    ("url", "Job URL", 45),
    ("match_score", "Match Score", 12),
    ("ats_score", "ATS Score", 12),
    ("missing_skills", "Missing Skills", 30),
    ("salary_estimate", "Salary Estimate", 16),
    ("interview_prob", "Interview Probability", 18),
    ("fit_notes", "Fit Notes", 40),
    ("priority", "Priority", 10),

    ("job_id", "Job ID", 14),
    ("status", "Status", 16),
    ("app_url", "App URL", 45),
    ("date_applied", "Date Applied", 12),
]

APPLICATIONS_COLUMNS = [
    ("date_found", "Date Found", 12),
    ("company", "Company", 22),
    ("title", "Job Title", 35),
    ("date_applied", "Date Applied", 12),
    ("resume_version", "Resume Version", 18),
    ("cover_letter", "Cover Letter", 12),
    ("status", "Status", 16),
    ("interview_date", "Interview Date", 14),
    ("interview_round", "Round", 8),
    ("offer_amount", "Offer Amount", 14),
    ("offer_date", "Offer Date", 12),
    ("rejected_date", "Rejected Date", 12),
    ("rejection_reason", "Rejection Reason", 30),
    ("notes", "Notes", 40),
    ("url", "Job URL", 45),
]

RESUME_COLUMNS = [
    ("date", "Date", 12),
    ("company", "Company", 22),
    ("title", "Job Title", 35),
    ("resume_file", "Resume File", 30),
    ("cover_letter_file", "Cover Letter File", 30),
    ("keywords_added", "Keywords Added", 30),
    ("keywords_removed", "Keywords Removed", 30),
    ("summary_used", "Summary Used", 50),
    ("highlights_changed", "Highlights Changed", 40),
    ("notes", "Notes", 40),
]

# Status values for Applications sheet
STATUS_VALUES = ["Not Applied", "Applied", "Phone Screen", "Interview", "Final Round", "Offer", "Rejected", "Withdrawn"]

# ─── Styling ───

HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)

PRIORITY_COLORS = {
    "High": PatternFill(start_color="FFD7D7", end_color="FFD7D7", fill_type="solid"),
    "Medium": PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"),
    "Low": PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid"),
}

SCORE_COLORS = {
    "high": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),   # green
    "medium": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),  # yellow
    "low": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),     # red
}


def init_journal(path=JOURNAL_PATH):
    """Create a fresh journal with all three sheets."""
    wb = Workbook()

    # ── Sheet 1: Jobs ──
    ws_jobs = wb.active
    ws_jobs.title = "Jobs"
    _write_headers(ws_jobs, JOBS_COLUMNS)
    _format_sheet(ws_jobs, JOBS_COLUMNS)

    # ── Sheet 2: Applications ──
    ws_apps = wb.create_sheet("Applications")
    _write_headers(ws_apps, APPLICATIONS_COLUMNS)
    _format_sheet(ws_apps, APPLICATIONS_COLUMNS)

    # ── Sheet 3: Resume Versions ──
    ws_resume = wb.create_sheet("Resume Versions")
    _write_headers(ws_resume, RESUME_COLUMNS)
    _format_sheet(ws_resume, RESUME_COLUMNS)

    # ── Sheet 4: Reference ──
    ws_ref = wb.create_sheet("Reference")
    ws_ref["A1"] = "Job Search Journal — Reference"
    ws_ref["A1"].font = Font(bold=True, size=14)
    ref_data = [
        ["", ""],
        ["Status Values (Applications sheet)", ""],
        ["Not Applied", "Job found but not yet applied"],
        ["Applied", "Application submitted"],
        ["Phone Screen", "Initial phone/screening call"],
        ["Interview", "Technical or on-site interview"],
        ["Final Round", "Final stage interview"],
        ["Offer", "Offer received"],
        ["Rejected", "Application rejected"],
        ["Withdrawn", "Withdrew application"],
        ["", ""],
        ["Priority Values (Jobs sheet)", ""],
        ["High", "Top match, apply within 24h"],
        ["Medium", "Good match, apply this week"],
        ["Low", "Possible match, monitor"],
        ["", ""],
        ["Search Mode (Jobs sheet)", ""],
        ["boston", "Found via Greater Boston LinkedIn search"],
        ["remote", "Found via Remote USA LinkedIn search"],
        ["greenhouse", "Found via Greenhouse ATS API"],
        ["lever", "Found via Lever ATS API"],
        ["ashby", "Found via Ashby ATS API"],
    ]
    for row in ref_data:
        ws_ref.append(row)
    ws_ref.column_dimensions["A"].width = 30
    ws_ref.column_dimensions["B"].width = 50

    wb.save(str(path))
    print(f"Journal created: {path}")
    return path


def _write_headers(ws, columns):
    """Write header row from column definitions."""
    for idx, (key, label, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=idx, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER


def _format_sheet(ws, columns):
    """Apply column widths, freeze panes, auto-filter, and text wrapping."""
    for idx, (key, label, width) in enumerate(columns, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}1"
    # Enable text wrapping for all data cells
    from openpyxl.styles import Alignment
    wrap = Alignment(wrap_text=True, vertical='top')
    for row_idx in range(2, ws.max_row + 1):
        for col_idx in range(1, len(columns) + 1):
            ws.cell(row=row_idx, column=col_idx).alignment = wrap


def add_jobs(jobs_data, path=JOURNAL_PATH, mode="append"):
    """Add jobs to the Jobs sheet. Skips duplicates by App URL, then URL, then company+title+location."""
    if not path.exists():
        init_journal(path)

    wb = load_workbook(str(path))
    ws = wb["Jobs"]

    # Get existing entries for dedup
    url_col = _find_col_by_key(JOBS_COLUMNS, "url")
    job_id_col = _find_col_by_key(JOBS_COLUMNS, "job_id")
    app_url_col = _find_col_by_key(JOBS_COLUMNS, "app_url")
    company_col = _find_col_by_key(JOBS_COLUMNS, "company")
    title_col = _find_col_by_key(JOBS_COLUMNS, "title")
    location_col = _find_col_by_key(JOBS_COLUMNS, "location")

    existing_urls = set()
    existing_job_ids = set()
    existing_app_urls = set()
    existing_company_title_loc = set()

    for row in ws.iter_rows(min_row=2, values_only=False):
        url_val = row[url_col - 1].value
        if url_val:
            existing_urls.add(str(url_val).strip())
        job_id_val = row[job_id_col - 1].value
        if job_id_val:
            existing_job_ids.add(str(job_id_val).strip())
        app_url_val = row[app_url_col - 1].value if app_url_col <= len(row) else None
        if app_url_val:
            existing_app_urls.add(str(app_url_val).strip())
        company_val = row[company_col - 1].value
        title_val = row[title_col - 1].value
        location_val = row[location_col - 1].value
        if company_val and title_val:
            key = f"{str(company_val).strip().lower()}|{str(title_val).strip().lower()}|{str(location_val or '').strip().lower()}"
            existing_company_title_loc.add(key)

    # Find next empty row
    next_row = ws.max_row + 1
    if ws.max_row == 1:  # only headers
        next_row = 2

    added = 0
    skipped = 0
    date_str = datetime.now().strftime("%Y-%m-%d")

    for job in jobs_data:
        url = job.get("url", "").strip()
        app_url = job.get("app_url", "").strip()
        company = job.get("company", "").strip()
        title = job.get("title", "").strip()
        location = job.get("location", "").strip()

        # Dedup by App URL (highest priority — cross-source)
        if app_url and app_url in existing_app_urls:
            skipped += 1
            continue

        # Dedup by source URL
        if url in existing_urls:
            skipped += 1
            continue

        # Extract job ID from URL
        job_id = ""
        if url:
            parts = url.rstrip("/").split("-")
            if parts:
                job_id = parts[-1]

        # Also check by job ID
        if job_id and job_id in existing_job_ids:
            skipped += 1
            continue

        # Fallback: dedup by company + title + location (catches cross-source dupes without App URL)
        if company and title:
            key = f"{company.lower()}|{title.lower()}|{location.lower()}"
            if key in existing_company_title_loc:
                skipped += 1
                continue

        # Map job data to columns
        row_data = {}
        for key, label, width in JOBS_COLUMNS:
            if key == "date_found":
                row_data[key] = date_str
            elif key == "job_id":
                row_data[key] = job_id
            elif key == "match_score":
                row_data[key] = ""  # to be filled by scoring
            elif key == "ats_score":
                row_data[key] = ""
            elif key == "missing_skills":
                row_data[key] = ""
            elif key == "salary_estimate":
                row_data[key] = ""
            elif key == "interview_prob":
                row_data[key] = ""
            elif key == "fit_notes":
                row_data[key] = ""
            elif key == "priority":
                row_data[key] = ""
            elif key == "must_apply_24h":
                row_data[key] = ""
            else:
                row_data[key] = job.get(key, "")

        # Write row
        for idx, (key, label, width) in enumerate(JOBS_COLUMNS, 1):
            ws.cell(row=next_row, column=idx, value=row_data[key])

        # Format priority cell if set
        if row_data.get("priority") in PRIORITY_COLORS:
            ws.cell(row=next_row, column=_find_col_by_key(JOBS_COLUMNS, "priority")).fill = PRIORITY_COLORS[row_data["priority"]]

        next_row += 1
        added += 1
        existing_urls.add(url)
        if job_id:
            existing_job_ids.add(job_id)
        if app_url:
            existing_app_urls.add(app_url)
        if company and title:
            key = f"{company.lower()}|{title.lower()}|{location.lower()}"
            existing_company_title_loc.add(key)

    # Ensure auto-filters on all sheets
    from openpyxl.utils import get_column_letter
    for sheet_name in ['Jobs', 'Applications', 'Resume Versions']:
        ws_filter = wb[sheet_name]
        max_col = ws_filter.max_column
        ws_filter.auto_filter.ref = f'A1:{get_column_letter(max_col)}1'
    
    wb.save(str(path))
    print(f"Added {added} jobs, skipped {skipped} duplicates")
    return added, skipped


def show_status(path=JOURNAL_PATH):
    """Print summary stats from the journal."""
    if not path.exists():
        print("No journal found. Run: python3 journal.py --init")
        return

    wb = load_workbook(str(path), read_only=True)

    print(f"Journal: {path}\n")

    # Jobs sheet
    ws = wb["Jobs"]
    total = ws.max_row - 1
    print(f"Jobs sheet: {total} jobs")

    # Count by source
    sources = {}
    scored = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        mode = row[4] or "unknown"  # search_mode column
        sources[mode] = sources.get(mode, 0) + 1
        if row[6]:  # match_score
            scored += 1

    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")
    print(f"  Scored: {scored}/{total}")

    # Applications sheet
    ws = wb["Applications"]
    app_count = ws.max_row - 1
    print(f"\nApplications sheet: {app_count} entries")

    statuses = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        status = row[6] or "No Status"  # status column
        statuses[status] = statuses.get(status, 0) + 1
    for st, count in sorted(statuses.items()):
        print(f"  {st}: {count}")

    # Resume sheet
    ws = wb["Resume Versions"]
    resume_count = ws.max_row - 1
    print(f"\nResume Versions sheet: {resume_count} entries")

    wb.close()


def _find_col_by_key(columns, key):
    """Find 1-based column index by key."""
    for idx, (k, label, width) in enumerate(columns, 1):
        if k == key:
            return idx
    return None


def main():
    parser = argparse.ArgumentParser(description="Job Journal — Excel tracking")
    parser.add_argument("--init", action="store_true", help="Create a new journal")
    parser.add_argument("--add", help="Add jobs from JSON file")
    parser.add_argument("--status", action="store_true", help="Show summary stats")
    parser.add_argument("--path", default=str(JOURNAL_PATH), help="Journal file path")
    args = parser.parse_args()

    path = Path(args.path)

    if args.init:
        init_journal(path)
    elif args.add:
        with open(args.add) as f:
            jobs = json.load(f)
        add_jobs(jobs, path)
    elif args.status:
        show_status(path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()