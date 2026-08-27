#!/usr/bin/env python3
"""
LinkedIn Jobs Search Pipeline — guest API, no browser/login required.

Searches LinkedIn Jobs for PM roles across every location defined in
config.json → search.locations. Each job is tagged with the search mode
of the location it came from ("boston", "remote", or the location name),
so downstream reporting (CSV/Markdown, journal Source column) can group
by mode.

Extracts job listings via LinkedIn's guest API, outputs CSV + Markdown.

Usage:
  python3 scripts/search_linkedin.py          # fetch fresh jobs via guest API
"""

import argparse
import csv
import html
import json
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

# Guest API pagination endpoint — returns the same <li> job cards as the browser page
GUEST_API = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
             "?keywords={keywords}&location={location}&sortBy=DD&start={start}")


def load_config():
    """Load search config from config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)

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
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Fetch fresh listings from LinkedIn's guest API (no browser needed),
    # tagging each job with the search mode of the location it came from.
    print("Fetching jobs from LinkedIn guest API...")
    jobs = []
    for loc in config.get("search", {}).get("locations", []):
        location_str = loc.get("linkedin_filter", loc.get("name", "United States"))
        search_mode = "remote" if loc.get("remote_only") else str(loc.get("name", "boston")).lower()
        print(f"  Searching: {location_str} (mode: {search_mode})")
        for job in fetch_jobs_from_guest_api(args.keywords, location_str):
            job["search_mode"] = search_mode
            jobs.append(job)
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
