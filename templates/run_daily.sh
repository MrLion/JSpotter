#!/bin/bash
# Daily pipeline runner — called by the cron job.
# This is the GENERIC template. Copy to <PROJECT_PATH>/run_daily.sh and set
# PYBIN + the project path before use. Kept out of the public repo as-is
# because it contains local absolute paths.

PYBIN="<PATH_TO_PYTHON3>"
cd "<PROJECT_PATH>" || exit 1

echo "=== Step 1: LinkedIn Search ==="
PYTHONPATH="" "$PYBIN" scripts/search_linkedin.py 2>&1

echo "=== Step 2: Add to Journal ==="
PYTHONPATH="" "$PYBIN" scripts/journal.py --add output/linkedin_extract.json 2>&1

echo "=== Step 3: Score New Jobs ==="
PYTHONPATH="" "$PYBIN" scripts/run_scoring.py 2>&1

echo "=== Step 4: Extract Requirements ==="
PYTHONPATH="" "$PYBIN" scripts/extract_requirements.py --backfill 40 2>&1

echo "=== DONE ==="
