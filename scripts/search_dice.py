#!/usr/bin/env python3
"""
Dice.com Jobs Search Pipeline — browser-based, login required.

Searches Dice.com for PM roles in two modes:
  1. Greater Boston (local)
  2. Remote in USA

Browser-based extraction (login required); processed jobs are output as JSON.

Usage:
  python3 search_dice.py              # print search URLs + JS for browser extraction
  python3 search_dice.py --boston     # Boston only
  python3 search_dice.py --remote     # Remote only
  python3 search_dice.py --keywords "principal product manager AI"
  python3 search_dice.py --input output/dice_extract.json   # process extracted jobs
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_PATH = BASE_DIR / "config.json"

# Dice search URL template
DICE_SEARCH = "https://www.dice.com/jobs?q={keywords}&location={location}"

# JavaScript to extract job listings from Dice search results
# Dice uses aria-label="View Details for <title> (<hash>)" on links
EXTRACT_JS = r"""
(() => {
  const results = [];
  const links = document.querySelectorAll('a[aria-label^="View Details"]');

  links.forEach(link => {
    const ariaLabel = link.getAttribute('aria-label') || '';
    const titleMatch = ariaLabel.match(/View Details for (.+?) \([a-f0-9]+\)$/);
    const title = titleMatch ? titleMatch[1] : '';

    const href = link.getAttribute('href') || '';
    const url = href.startsWith('http') ? href : 'https://www.dice.com' + href;

    let card = link;
    for (let i = 0; i < 6; i++) {
      card = card.parentElement;
      if (!card) break;
      const img = card.querySelector('img[alt]:not([alt=""]):not([alt*="Logo"])');
      if (img && img.alt.length > 2) {
        const company = img.alt;
        const paras = card.querySelectorAll('p');
        let location = '';
        paras.forEach(p => {
          const t = p.textContent?.trim() || '';
          if ((t.includes('Remote') || t.includes('Hybrid in') || /^[A-Z][a-z]+,\s[A-Z][a-z]/.test(t)) && !location) {
            location = t.split('•')[0].trim();
          }
        });

        if (title.length > 5) {
          results.push({title, company, location, url: url.split('?')[0], search_mode: 'dice'});
        }
        break;
      }
    }
  });

  return results;
})()
"""

# JavaScript to extract the apply URL from a Dice job detail page
# Returns the company ATS URL or empty string if it redirects to another job board
APPLY_EXTRACT_JS = r"""
(() => {
  const applyLink = Array.from(document.querySelectorAll('a')).find(a => 
    a.textContent?.trim() === 'Apply' || a.textContent?.trim() === 'Apply Now'
  );
  return applyLink ? applyLink.href : '';
})()
"""


def load_config():
    """Load search config from config.json."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def build_search_urls(config, keywords, boston=True, remote=True):
    """Build Dice search URLs from config locations."""
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
        urls.append({
            "mode": "remote" if is_remote else "boston",
            "name": name,
            "url": DICE_SEARCH.format(keywords=kw, location=loc_encoded)
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


# Job board domains loaded from config.json at runtime
# Note: greenhouse.io, lever.co, workday, eightfold.ai, paylocity.com are company ATS platforms, NOT job boards


def is_job_board(url, config):
    """Check if a URL points to another job board rather than a company ATS."""
    if not url:
        return False
    job_board_domains = config.get("dedup", {}).get("job_board_domains", [])
    url_lower = url.lower()
    return any(domain in url_lower for domain in job_board_domains)


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


def save_raw_json(jobs, date_str):
    """Save raw JSON for downstream processing (scoring, journal, etc)."""
    filename = OUTPUT_DIR / "dice_extract.json"
    with open(filename, "w") as f:
        json.dump(jobs, f, indent=2)
    return filename


def main():
    config = load_config()

    search_config = config.get("search", {})
    if not search_config.get("keywords"):
        print("ERROR: search.keywords not found in config.json")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Dice.com Jobs Search Pipeline")
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
        print("INSTRUCTIONS:")
        creds = config.get("credentials", {}).get("dice", {})
        if creds.get("email"):
            print(f"1. Login to dice.com ({creds['email']})")
        else:
            print("1. Login to dice.com (set credentials.dice in config.json)")
            return
        print("2. Navigate to each search URL")
        print("3. Run EXTRACT_JS to get job listings")
        print("4. For each job, navigate to its detail page URL")
        print("5. Click the Apply button — wait for redirect")
        print("6. Run APPLY_EXTRACT_JS to get the apply URL")
        print("7. If apply URL is another job board (efinancialcareers, etc.), skip that job")
        print("8. If apply URL is a company ATS, store it as app_url")
        print("9. Save results to output/dice_extract.json with app_url field per job")
        print("10. Re-run: python3 search_dice.py --input output/dice_extract.json")
        print()
        print("EXTRACT_JS:")
        print(EXTRACT_JS)
        print()
        print("APPLY_EXTRACT_JS:")
        print(APPLY_EXTRACT_JS)
        return

    # Process extracted jobs
    jobs = dedupe_jobs(jobs)
    jobs = filter_by_keywords(jobs, config)

    # Filter out jobs where apply URL goes to another job board
    filtered = []
    for j in jobs:
        app_url = j.get("app_url", "")
        if app_url and is_job_board(app_url, config):
            print(f"  Skipped (job board redirect): {j.get('company')} — {j.get('title')}")
            continue
        filtered.append(j)
    jobs = filtered

    print(f"After dedup + filter: {len(jobs)} jobs")

    json_path = save_raw_json(jobs, date_str)

    print(f"\nSaved:")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()