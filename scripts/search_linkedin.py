#!/usr/bin/env python3
"""
LinkedIn Jobs Search Pipeline — browser-based, no login required.

Searches LinkedIn Jobs for PM roles in two modes:
  1. Greater Boston (local)
  2. Remote in USA

Extracts job listings via JavaScript, outputs CSV + Markdown.

Usage:
  python3 scripts/search_linkedin.py          # fetch fresh jobs via guest API
  python3 scripts/search_linkedin.py --input output/linkedin_extract.json  # process pre-extracted jobs
"""

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"

# LinkedIn Jobs search URL template
# f_WT=2 = Remote filter, sortBy=DD = Date posted (newest first)
LINKEDIN_SEARCH = "https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}{remote_filter}&sortBy=DD"

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


# Guest API pagination endpoint — returns the same <li> job cards as the browser page
GUEST_API = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
             "?keywords={keywords}&location={location}&sortBy=DD&start={start}")

LI_RE = re.compile(r"<li[^>]*>.*?</li>", re.S)
TITLE_RE = re.compile(r'<h3[^>]*class="[^"]*base-search-card__title[^"]*"[^>]*>(.*?)</h3>', re.S)
COMPANY_RE = re.compile(r'<h4[^>]*class="[^"]*base-search-card__subtitle[^"]*"[^>]*>(.*?)</h4>', re.S)
LOC_RE = re.compile(r'<span[^>]*class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)</span>', re.S)
LINK_RE = re.compile(r'<a[^>]*class="[^"]*base-card__full-link[^"]*"[^>]*href="([^"]+)"', re.S)
STRIP_RE = re.compile(r"<[^>]+>")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _clean(s):
    return html.unescape(STRIP_RE.sub(" ", s or "")).strip()


def _curl(url):
    r = subprocess.run(
        ["curl", "-s", "--max-time", "40", "-A", UA,
         "-H", "Accept-Language: en-US,en;q=0.9",
         "-H", "Accept: text/html,application/xhtml+xml",
         url],
        capture_output=True, text=True)
    return r.stdout or ""


def _parse_cards(page_html):
    out = []
    for li in LI_RE.findall(page_html):
        if "jobs/view/" not in li:
            continue
        m = LINK_RE.search(li)
        if not m:
            continue
        url = m.group(1).split("?")[0]
        title = _clean(TITLE_RE.search(li).group(1)) if TITLE_RE.search(li) else ""
        company = _clean(COMPANY_RE.search(li).group(1)) if COMPANY_RE.search(li) else ""
        location = _clean(LOC_RE.search(li).group(1)) if LOC_RE.search(li) else ""
        if title and title != "See who Arcadia has hired for this role":
            out.append({"title": title, "company": company,
                        "location": location, "url": url})
    return out


def fetch_jobs_from_guest_api(keywords, location, max_start=250):
    """Fetch job listings from LinkedIn's guest API via curl. No browser needed."""
    from urllib.parse import quote
    kw = quote(keywords)
    loc = quote(location)
    all_jobs, seen = [], set()
    for start in range(0, max_start + 1, 25):
        htmltxt = _curl(GUEST_API.format(keywords=kw, location=loc, start=start))
        cards = _parse_cards(htmltxt)
        for c in cards:
            if c["url"] not in seen:
                seen.add(c["url"])
                all_jobs.append(c)
        print(f"  start={start}: {len(cards)} cards, total unique {len(all_jobs)}", flush=True)
        if len(cards) < 10:  # page exhausted / blocked
            break
        time.sleep(1.5)
    return all_jobs


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


def filter_by_keywords(jobs, keywords, config):
    """Soft filter: keep product management roles based on config title_filter_terms."""
    terms = config.get("search", {}).get("title_filter_terms")
    if not terms:
        raise ValueError("search.title_filter_terms not found in config.json")
    filtered = []
    for j in jobs:
        title_lower = j.get("title", "").lower()
        if "product" in title_lower and any(term in title_lower for term in terms):
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
        # Fetch fresh listings from LinkedIn's guest API (no browser needed)
        print("Fetching jobs from LinkedIn guest API...")
        jobs = []
        for loc in config.get("search", {}).get("locations", []):
            location_str = loc.get("linkedin_filter", loc.get("name", "United States"))
            print(f"  Searching: {location_str}")
            jobs.extend(fetch_jobs_from_guest_api(args.keywords, location_str))
        print(f"Fetched {len(jobs)} raw jobs")
    
    # Process extracted jobs
    jobs = dedupe_jobs(jobs)
    jobs = filter_by_keywords(jobs, args.keywords, config)
    
    print(f"After dedup + filter: {len(jobs)} jobs")
    
    csv_path = save_csv(jobs, date_str)
    md_path = save_markdown(jobs, date_str)
    json_path = save_raw_json(jobs, date_str)
    
    # Also write the canonical extract file the journal reads
    with open(OUTPUT_DIR / "linkedin_extract.json", "w") as f:
        json.dump(jobs, f, indent=2)
    
    print(f"\nSaved:")
    print(f"  CSV:  {csv_path}")
    print(f"  MD:   {md_path}")
    print(f"  JSON: {json_path}")
    print(f"  EXTRACT: {OUTPUT_DIR / 'linkedin_extract.json'}")


if __name__ == "__main__":
    main()
