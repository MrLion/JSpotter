#!/usr/bin/env python3
"""
LinkedIn Jobs Search Pipeline — browser-based, no login required.

Searches LinkedIn Jobs for PM roles in two modes:
  1. Greater Boston (local)
  2. Remote in USA

Extracts job listings via JavaScript, outputs CSV + Markdown.

Usage:
  python3 search_linkedin.py              # search both Boston + Remote
  python3 search_linkedin.py --boston      # Boston only
  python3 search_linkedin.py --remote      # Remote only
  python3 search_linkedin.py --keywords "principal product manager AI"
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"

# LinkedIn Jobs search URL template
# f_WT=2 = Remote filter
LINKEDIN_SEARCH = "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}{remote_filter}"

# JavaScript to extract job listings from the page
EXTRACT_JS = """
JSON.stringify(
  Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'))
    .map(a => {
      const li = a.closest('li, .job-search-card, [class*="job-card"]');
      const title = li?.querySelector('h3, [class*="title"]')?.textContent?.trim() || a.textContent.trim();
      const company = li?.querySelector('h4, [class*="company"]')?.textContent?.trim() || '';
      const location = li?.querySelector('[class*="location"]')?.textContent?.trim() || '';
      return {title, company, location, url: a.href.split('?')[0]};
    })
    .filter(j => j.title && j.title !== 'See who Arcadia has hired for this role')
)
"""

# JavaScript to dismiss sign-in dialog
DISMISS_JS = """
(() => {
  const btn = document.querySelector('button[aria-label="Dismiss"], button[type="button"]');
  const dialogs = document.querySelectorAll('[role="dialog"]');
  for (const d of dialogs) {
    const dismissBtn = d.querySelector('button');
    if (dismissBtn && (dismissBtn.textContent.includes('Dismiss') || dismissBtn.textContent.includes('×'))) {
      dismissBtn.click();
      return 'dismissed';
    }
  }
  return 'no dialog';
})()
"""

# JavaScript to click "See more jobs" button
SEE_MORE_JS = """
(() => {
  const btn = document.querySelector('button[aria-label="See more jobs"]');
  if (btn) { btn.click(); return 'clicked'; }
  return 'no button';
})()
"""

# JavaScript to get current job count
COUNT_JS = "document.querySelectorAll('a[href*=\"/jobs/view/\"]').length"

# JavaScript to scroll the job results list
SCROLL_JS = """
(() => {
  const list = document.querySelector('.jobs-search-results-list, .scaffold-layout__list-container, [class*="jobs-search-results"]');
  if (list) { list.scrollTop = list.scrollHeight; return 'scrolled list'; }
  window.scrollTo(0, document.body.scrollHeight);
  return 'scrolled window';
})()
"""


def run_applescript(script):
    """Run an AppleScript command and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip()


def extract_jobs_from_browser():
    """
    Extract jobs from the currently loaded LinkedIn page in the Hermes browser.
    Uses the browser_console tool via subprocess to call the Hermes API.
    Since we can't call browser tools from Python directly, we use a different approach:
    we'll write results to a temp file via JavaScript and read it.
    
    Actually — this script is designed to be orchestrated BY the Hermes agent.
    The agent will:
    1. Navigate to LinkedIn search URL
    2. Dismiss sign-in dialog
    3. Scroll to load results
    4. Run extract JS
    5. Save results
    
    This script handles the orchestration logic and output formatting.
    The actual browser interaction is done by the agent calling browser tools.
    """
    pass


def load_config():
    """Load search config from config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def build_search_urls(config, keywords, boston=True, remote=True):
    """Build LinkedIn search URLs from config locations."""
    from urllib.parse import quote
    kw = quote(keywords)
    urls = []

    for loc in config.get("search", {}).get("locations", []):
        name = loc.get("name", "Unknown")
        is_remote = loc.get("remote_only", False)
        location_str = loc.get("linkedin_filter", name)

        if is_remote and not remote:
            continue
        if not is_remote and not boston:
            continue

        loc_encoded = quote(location_str)
        remote_filter = "&f_WT=2" if is_remote else ""
        urls.append({
            "mode": "remote" if is_remote else "boston",
            "name": name,
            "url": LINKEDIN_SEARCH.format(keywords=kw, location=loc_encoded, remote_filter=remote_filter)
        })

    return urls


def dedupe_jobs(jobs):
    """Remove duplicate jobs by URL."""
    seen = set()
    unique = []
    for j in jobs:
        key = j.get("url", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(j)
    return unique


def filter_by_keywords(jobs, keywords):
    """Soft filter: keep jobs that match any keyword in title."""
    kw_lower = keywords.lower()
    terms = [t.strip() for t in kw_lower.split() if len(t) > 2]
    # Keep jobs whose title contains "product" — already filtered by LinkedIn search
    # This is a secondary filter for quality
    filtered = []
    for j in jobs:
        title_lower = j.get("title", "").lower()
        if "product" in title_lower and "manager" in title_lower:
            filtered.append(j)
    return filtered


def save_csv(jobs, date_str):
    """Save jobs to CSV."""
    filename = OUTPUT_DIR / f"linkedin_jobs_{date_str}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date_found", "search_mode", "company", "title", "location", "url"
        ])
        writer.writeheader()
        for j in jobs:
            writer.writerow({
                "date_found": date_str,
                "search_mode": j.get("search_mode", ""),
                "company": j.get("company", ""),
                "title": j.get("title", ""),
                "location": j.get("location", ""),
                "url": j.get("url", ""),
            })
    return filename


def save_markdown(jobs, date_str):
    """Save jobs to markdown summary grouped by company."""
    filename = OUTPUT_DIR / f"linkedin_jobs_{date_str}.md"
    with open(filename, "w") as f:
        f.write(f"# LinkedIn Job Search Results — {date_str}\n\n")
        f.write(f"**{len(jobs)} jobs found**\n\n")
        
        # Split by mode
        boston_jobs = [j for j in jobs if j.get("search_mode") == "boston"]
        remote_jobs = [j for j in jobs if j.get("search_mode") == "remote"]
        
        for mode_name, mode_jobs in [("Greater Boston", boston_jobs), ("Remote USA", remote_jobs)]:
            if not mode_jobs:
                continue
            f.write(f"---\n\n## {mode_name} ({len(mode_jobs)} jobs)\n\n")
            
            # Group by company
            by_company = {}
            for j in mode_jobs:
                company = j.get("company", "Unknown")
                by_company.setdefault(company, []).append(j)
            
            for company in sorted(by_company.keys()):
                company_jobs = by_company[company]
                f.write(f"### {company}\n\n")
                for j in company_jobs:
                    f.write(f"- **{j['title']}**\n")
                    f.write(f"  - Location: {j.get('location', 'N/A')}\n")
                    f.write(f"  - URL: {j['url']}\n\n")
    
    return filename


def save_raw_json(jobs, date_str):
    """Save raw JSON for downstream processing (scoring, etc)."""
    filename = OUTPUT_DIR / f"linkedin_jobs_{date_str}.json"
    with open(filename, "w") as f:
        json.dump(jobs, f, indent=2)
    return filename


def main():
    config = load_config()

    search_config = config.get("search", {})
    if not search_config.get("keywords"):
        print("ERROR: search.keywords not found in config.json")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="LinkedIn Jobs Search Pipeline")
    parser.add_argument("--keywords", default=search_config["keywords"], help="Search keywords")
    parser.add_argument("--boston", action="store_true", help="Search Greater Boston")
    parser.add_argument("--remote", action="store_true", help="Search Remote USA")
    parser.add_argument("--input", help="Read pre-extracted jobs from JSON file instead of browser")
    args = parser.parse_args()
    
    # If neither flag set, search both
    search_boston = args.boston or (not args.boston and not args.remote)
    search_remote = args.remote or (not args.boston and not args.remote)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    if args.input:
    # Read pre-extracted jobs from JSON file (from browser extraction)
        with open(args.input) as f:
            jobs = json.load(f)
        print(f"Loaded {len(jobs)} jobs from {args.input}")
    else:
        # Print search URLs for the agent to navigate to
        urls = build_search_urls(config, args.keywords, boston=search_boston, remote=search_remote)
        print("SEARCH_URLS:")
        for u in urls:
            print(f"  {u['mode']}: {u['url']}")
        print()
        print("EXTRACT_JS:")
        print(EXTRACT_JS)
        print()
        print("INSTRUCTIONS:")
        print("1. Navigate to each search URL")
        print("2. Dismiss sign-in dialog if it appears")
        print("3. Scroll down 3-4 times to load more results")
        print("4. Run EXTRACT_JS to get job listings")
        print("5. Save results to output/linkedin_extract.json")
        print("6. Re-run: python3 search_linkedin.py --input output/linkedin_extract.json")
        return
    
    # Process extracted jobs
    jobs = dedupe_jobs(jobs)
    jobs = filter_by_keywords(jobs, args.keywords)
    
    print(f"After dedup + filter: {len(jobs)} jobs")
    
    csv_path = save_csv(jobs, date_str)
    md_path = save_markdown(jobs, date_str)
    json_path = save_raw_json(jobs, date_str)
    
    print(f"\nSaved:")
    print(f"  CSV:  {csv_path}")
    print(f"  MD:   {md_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()