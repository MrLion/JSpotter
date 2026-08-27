#!/usr/bin/env python3
"""
Adzuna Jobs Search Pipeline — REST API, no browser/login.

Searches Adzuna for PM roles via the Adzuna API and writes the results
to output/adzuna_extract.json in the same shape the journal/scoring expects.

Usage:
  python3 scripts/search_adzuna.py              # fetch fresh jobs via Adzuna API
  python3 scripts/search_adzuna.py --keywords "principal product manager AI"
  python3 scripts/search_adzuna.py --where "Boston"   # override location
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"

# Adzuna search API endpoint. Country code is in the path (us = United States).
ADZUNA_API = ("https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
              "?app_id={app_id}&app_key={app_key}"
              "&what={keywords}&where={location}"
              "&results_per_page={per_page}&max_days_old={max_days_old}"
              "&content-type=application/json")

DEFAULT_COUNTRY = "us"
DEFAULT_PER_PAGE = 50
MAX_PAGES = 10  # up to 500 results; Adzuna returns fewer if exhausted
MAX_DAYS_OLD = 30


def load_config():
    """Load config from config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_credentials(config):
    """Return (app_id, app_key) from config.credentials.adzuna."""
    creds = config.get("credentials", {}).get("adzuna", {})
    app_id = creds.get("app_id", "")
    app_key = creds.get("app_key", "")
    if not app_id or not app_key:
        raise ValueError("credentials.adzuna.app_id and credentials.adzuna.app_key must be set in config.json")
    return app_id, app_key


def curl(url):
    """Fetch a URL with curl (stdlib only, no requests dependency)."""
    r = subprocess.run(
        ["curl", "-s", "--max-time", "40", url],
        capture_output=True, text=True)
    return r.stdout


def map_job(j, search_mode="adzuna"):
    """Map an Adzuna API result to the journal/scoring job shape."""
    location = (j.get("location") or {}).get("display_name", "")
    company = (j.get("company") or {}).get("display_name", "")
    category = (j.get("category") or {}).get("label", "")
    url = j.get("redirect_url", "")
    # Adzuna's redirect_url lands on adzuna.com; the company ATS URL isn't
    # directly available from the search API, so there's no app_url.
    return {
        "title": j.get("title", ""),
        "company": company,
        "location": location,
        "url": url,
        "search_mode": search_mode,
        "salary_min": j.get("salary_min"),
        "salary_max": j.get("salary_max"),
        "salary_is_predicted": j.get("salary_is_predicted"),
        "created": j.get("created"),
        "description": j.get("description", ""),
        "category": category,
    }


def fetch_jobs(keywords, location, config, max_days_old=MAX_DAYS_OLD):
    """Fetch job listings from the Adzuna API (paginated)."""
    from urllib.parse import quote
    app_id, app_key = get_credentials(config)
    country = config.get("search", {}).get("adzuna_country", DEFAULT_COUNTRY)
    per_page = config.get("search", {}).get("adzuna_per_page", DEFAULT_PER_PAGE)

    kw = quote(keywords)
    loc = quote(location or "")
    all_jobs = []
    seen = set()
    total_found = None

    for page in range(1, MAX_PAGES + 1):
        url = ADZUNA_API.format(
            country=country, page=page, app_id=app_id, app_key=app_key,
            keywords=kw, location=loc, per_page=per_page, max_days_old=max_days_old)
        out = curl(url)
        try:
            data = json.loads(out)
        except Exception as e:
            print(f"  page {page}: parse error ({e}); stopping", flush=True)
            break
        if total_found is None:
            total_found = data.get("count", 0)
            print(f"  Adzuna reports {total_found} total matches", flush=True)
        results = data.get("results", [])
        if not results:
            break
        for j in results:
            mapped = map_job(j)
            if mapped["url"] and mapped["url"] not in seen:
                seen.add(mapped["url"])
                all_jobs.append(mapped)
        print(f"  page {page}: {len(results)} results, total unique {len(all_jobs)}", flush=True)
        if len(results) < per_page:
            break

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


def filter_by_keywords(jobs, config):
    """Keep product management roles based on config title_filter_terms."""
    terms = config.get("search", {}).get("title_filter_terms")
    if not terms:
        raise ValueError("search.title_filter_terms not found in config.json")
    filtered = []
    for j in jobs:
        title_lower = j.get("title", "").lower()
        if "product" in title_lower and any(term in title_lower for term in terms):
            filtered.append(j)
    return filtered


def main():
    config = load_config()

    search_config = config.get("search", {})
    if not search_config.get("keywords"):
        print("ERROR: search.keywords not found in config.json")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Adzuna Jobs Search Pipeline")
    parser.add_argument("--keywords", default=search_config["keywords"], help="Search keywords")
    parser.add_argument("--where", default="", help="Location filter (empty = nationwide)")
    parser.add_argument("--max-days-old", type=int, default=MAX_DAYS_OLD, help="Only jobs posted in last N days")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Location: CLI override, else config search location, else nationwide.
    location = args.where
    if not location:
        locs = search_config.get("locations", [])
        if locs:
            location = locs[0].get("linkedin_filter", locs[0].get("name", ""))

    print("Fetching jobs from Adzuna API...")
    jobs = fetch_jobs(args.keywords, location, config, max_days_old=args.max_days_old)
    print(f"Fetched {len(jobs)} raw jobs")

    jobs = dedupe_jobs(jobs)
    jobs = filter_by_keywords(jobs, config)
    print(f"After dedup + filter: {len(jobs)} jobs")

    # Write canonical extract for the journal, plus a dated copy.
    extract_path = OUTPUT_DIR / "adzuna_extract.json"
    with open(extract_path, "w") as f:
        json.dump(jobs, f, indent=2)
    dated_path = OUTPUT_DIR / f"adzuna_jobs_{date_str}.json"
    with open(dated_path, "w") as f:
        json.dump(jobs, f, indent=2)

    print(f"\nSaved:")
    print(f"  EXTRACT: {extract_path}")
    print(f"  DATED:   {dated_path}")


if __name__ == "__main__":
    main()
