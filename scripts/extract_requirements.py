#!/usr/bin/env python3
"""
Requirement Extraction — classifies JD requirements as required/preferred/bonus.

Primary engine: ollama-cloud LLM (configurable via env). Fallback: pure-Python
heuristic classifier (also used when the LLM is unreachable or returns nothing
verifiable). Every extracted requirement is quote-verified against the source
JD text — hallucinated requirements that don't appear in the JD are dropped.

Output cache: output/requirements_cache.json, keyed by job URL:
  {
    "<url>": {
      "engine": "ollama" | "heuristic",
      "llm_error": "<last LLM failure reason, when engine=heuristic>",
      "extracted_ts": "2026-08-27T...",
      "requirements": [
        {"text": "5+ years product management",
         "type": "required" | "preferred" | "bonus",
         "category": "skill" | "domain" | "experience" | "education" | "other",
         "quote": "<verbatim span from the JD>",
         "confidence": 0.0-1.0}
      ]
    }
  }

Usage:
  python3 scripts/extract_requirements.py                 # extract uncached JDs (cap 40/run)
  python3 scripts/extract_requirements.py --backfill 200  # process up to 200 uncached
  python3 scripts/extract_requirements.py --url <job_url> # one JD (re-extracts)
  python3 scripts/extract_requirements.py --report        # cache stats + accuracy proxy

Configuration (env, all optional):
  EMR_ENDPOINT   OpenAI-compatible base URL (default https://ollama.com/v1;
                 e.g. http://localhost:11434/v1 for local Ollama)
  EMR_MODEL      model tag (default glm-5.3-flash)
  EMR_TIMEOUT    per-JD LLM timeout seconds (default 120)
  EMR_MAX_TOKENS max completion tokens (default 2000)
  EMR_PACE_S     seconds between LLM calls (default 2; rate-limit pacing)
  OLLAMA_API_KEY bearer token; falls back to ~/.hermes/.env

Standard library only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DESCS_PATH = BASE_DIR / "output" / "descriptions_cache.json"
REQS_PATH = BASE_DIR / "output" / "requirements_cache.json"

ENDPOINT = os.environ.get("EMR_ENDPOINT", "https://ollama.com/v1")
MODEL = os.environ.get("EMR_MODEL", "glm-5.3-flash")
TIMEOUT_S = int(os.environ.get("EMR_TIMEOUT", "120"))
MAX_TOKENS = int(os.environ.get("EMR_MAX_TOKENS", "4000"))
PACE_S = float(os.environ.get("EMR_PACE_S", "0"))
MAX_WORKERS = int(os.environ.get("EMR_WORKERS", "5"))

# Built by concatenation so source files never contain literal think-tags
# (edit tools strip HTML-looking spans).
CLOSE_THINK = "<" + "/think>"

# Cache writes are serialized — extract_one is called from worker threads
_CACHE_LOCK = threading.Lock()


def _load_api_key():
    """OLLAMA_API_KEY from env, else parsed from ~/.hermes/.env."""
    v = os.environ.get("OLLAMA_API_KEY")
    if v:
        return v
    try:
        for line in (Path.home() / ".hermes" / ".env").read_text().splitlines():
            if line.strip().startswith("OLLAMA_API_KEY="):
                return line.partition("=")[2].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


API_KEY = _load_api_key()

VALID_TYPES = {"required", "preferred", "bonus"}
VALID_CATS = {"skill", "domain", "experience", "education", "other"}

# ── Heuristic fallback ──────────────────────────────────────────────────────

_PREFERRED_CUES = ("preferred", "nice to have", "bonus", "plus", "ideal",
                   "desired", "a plus", "advantageous", "not required but")
_REQUIRED_CUES = ("required", "must", "minimum", "mandatory", "needs to have",
                  "should have", "you will need", "qualification")
_EDU_CUES = ("bachelor", "master", "mba", "degree", "phd", "b.s.", "m.s.", "university")
_CERT_CUES = ("certified", "certification", "pmp", "csm", "safe", "aipmm")


def _sentences(text):
    """Crude sentence split that tolerates flattened text."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    return [p.strip() for p in parts if 15 < len(p.strip()) < 400]


def _categorize(sentence_lower):
    if any(c in sentence_lower for c in _EDU_CUES):
        return "education"
    if any(c in sentence_lower for c in _CERT_CUES):
        return "education"
    if re.search(r"\d+\+?\s*years", sentence_lower):
        return "experience"
    return "skill"


def classify_requirements_heuristic(jd_text):
    """Fallback classifier over sentences. Lower accuracy than the LLM,
    works on flattened text. Returns list in the same schema."""
    out = []
    for s in _sentences(jd_text):
        s_lower = s.lower()
        is_pref = any(c in s_lower for c in _PREFERRED_CUES)
        is_req = any(c in s_lower for c in _REQUIRED_CUES)
        if not (is_pref or is_req):
            continue
        rtype = "preferred" if is_pref else "required"
        cat = _categorize(s_lower)
        out.append({
            "text": s[:120],
            "type": rtype,
            "category": cat,
            "quote": s[:200],
            "confidence": 0.55,
        })
    return out[:15]


# ── LLM extraction ──────────────────────────────────────────────────────────

_PROMPT_TMPL = """You extract job requirements. From the JOB DESCRIPTION below, list every requirement as a JSON object of this exact shape:

{{"requirements": [{{"text": "<concise requirement, max 20 words>", "type": "required|preferred|bonus", "category": "skill|domain|experience|education|other", "quote": "<short verbatim span copied EXACTLY from the JD>", "confidence": <0.0-1.0>}}]}}

Rules:
- "required" = mandatory ("must", "required", "minimum qualifications", basic qualifications).
- "preferred" = nice-to-have ("preferred", "plus", "bonus", "nice to have", "ideal", "desired").
- "bonus" = explicitly optional extras (equity, side projects, open-source).
- The "quote" MUST be copied character-for-character from the JD (max 25 words). Never paraphrase the quote.
- Include: years-of-experience, education, certifications, domain/industry knowledge, technical skills.
- Max 15 items. Output ONLY the JSON object.

JOB DESCRIPTION:
<<<
{jd}
>>>"""


def _ollama_generate(jd_text):
    """Call an OpenAI-compatible chat endpoint (ollama-cloud or local /v1).
    Returns (parsed_json_or_None, error_string_or_None)."""
    prompt = _PROMPT_TMPL.format(jd=jd_text[:12000])
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "max_tokens": MAX_TOKENS,
    })
    headers = ["-H", "Content-Type: application/json"]
    if API_KEY:
        headers += ["-H", "Authorization: Bearer " + API_KEY]
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", str(TIMEOUT_S), *headers,
             "-d", payload, ENDPOINT.rstrip("/") + "/chat/completions"],
            capture_output=True, text=True, timeout=TIMEOUT_S + 10)
        if not r.stdout.strip():
            return None, f"empty response (curl exit {r.returncode})"
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            return None, "non-JSON response: " + r.stdout[:150]
        if data.get("error"):
            return None, "API error: " + str(data["error"])[:200]
        msg = (data.get("choices") or [{}])[0].get("message", {})
        raw = (msg.get("content") or msg.get("reasoning_content")
               or msg.get("thinking") or "").strip()
        if not raw:
            return None, "no content in response: " + r.stdout[:300]
        # Thinking models may leak marker-wrapped reasoning into content;
        # keep only what follows the closing marker, if present.
        if CLOSE_THINK in raw:
            raw = raw.split(CLOSE_THINK)[-1].strip()
        # Models often wrap JSON in ```json ... ``` fences — strip them
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
        try:
            return json.loads(raw), None
        except json.JSONDecodeError:
            salvaged = _salvage_requirements_json(raw)
            if salvaged is not None:
                return salvaged, None
            return None, "unparseable model output: " + raw[:150]
    except subprocess.TimeoutExpired:
        return None, f"timeout after {TIMEOUT_S}s"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _salvage_requirements_json(raw):
    """Salvage requirement objects from truncated/invalid JSON.

    Requirement objects are flat (no nested braces), so individually parsing
    every {...} span recovers complete items even when the model output was
    cut off mid-array by a token limit. Returns {"requirements": [...]} or None.
    """
    objs = []
    for m in re.finditer(r"\{[^{}]*\}", raw, re.S):
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("text"):
            objs.append(obj)
    return {"requirements": objs} if objs else None


def _norm(s):
    """Normalize for quote verification: lowercase, collapse whitespace,
    strip common punctuation variants."""
    s = str(s or "").lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[^a-z0-9$%., ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _verify_and_clean(requirements, jd_text):
    """Keep only requirements whose quote actually appears in the JD."""
    jd_norm = _norm(jd_text)
    kept = []
    seen_texts = set()
    for r in requirements or []:
        if not isinstance(r, dict):
            continue
        text = str(r.get("text", "")).strip()
        quote = str(r.get("quote", "")).strip()
        rtype = str(r.get("type", "")).lower()
        cat = str(r.get("category", "")).lower()
        if not text or len(text) > 200 or len(quote) < 10:
            continue
        if rtype not in VALID_TYPES or cat not in VALID_CATS:
            continue
        if _norm(quote) not in jd_norm:
            continue  # hallucination guard: quote not found in JD
        key = _norm(text)[:80]
        if key in seen_texts:
            continue
        seen_texts.add(key)
        try:
            conf = max(0.0, min(1.0, float(r.get("confidence", 0.8))))
        except (TypeError, ValueError):
            conf = 0.8
        kept.append({"text": text, "type": rtype, "category": cat,
                     "quote": quote, "confidence": round(conf, 2)})
    return kept[:15]


# ── Cache & CLI ─────────────────────────────────────────────────────────────

def load_cache():
    try:
        with open(REQS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(REQS_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def extract_one(url, jd_text, cache, use_llm=True):
    """Extract requirements for one JD, update cache. Returns (engine, llm_error).
    Thread-safe: cache writes serialized."""
    rec = {"url": url, "extracted_ts": datetime.now().isoformat(), "requirements": []}
    engine = "heuristic"
    llm_error = None
    if use_llm:
        data, llm_error = _ollama_generate(jd_text)
        reqs = _verify_and_clean((data or {}).get("requirements"), jd_text)
        if reqs:
            rec["requirements"] = reqs
            engine = "ollama"
        elif llm_error:
            rec["llm_error"] = llm_error
    if not rec["requirements"]:
        rec["requirements"] = classify_requirements_heuristic(jd_text)
        engine = "heuristic"
    rec["engine"] = engine
    with _CACHE_LOCK:
        cache[url] = rec
        save_cache(cache)
    return engine, rec.get("llm_error")


def main():
    ap = argparse.ArgumentParser(description="JD requirement extraction (LLM + heuristic fallback)")
    ap.add_argument("--backfill", type=int, default=0, help="max JDs to process this run (0 = uncached only, cap 40)")
    ap.add_argument("--url", help="extract a single JD by URL (re-extracts)")
    ap.add_argument("--report", action="store_true", help="print cache stats")
    ap.add_argument("--no-llm", action="store_true", help="heuristic only (no LLM calls)")
    args = ap.parse_args()

    try:
        with open(DESCS_PATH) as f:
            descs = json.load(f)
    except Exception as e:
        print(f"ERROR: cannot read {DESCS_PATH}: {e}")
        sys.exit(1)

    cache = load_cache()

    if args.report:
        total = len(cache)
        engines = Counter(v.get("engine", "?") for v in cache.values())
        errors = Counter(v.get("llm_error", "")[:80] for v in cache.values() if v.get("llm_error"))
        n_reqs = [len(v.get("requirements", [])) for v in cache.values()]
        types = Counter(r["type"] for v in cache.values() for r in v.get("requirements", []))
        cats = Counter(r["category"] for v in cache.values() for r in v.get("requirements", []))
        print(f"Extracted JDs: {total}/{len(descs)}")
        print(f"Engines: {dict(engines)}")
        if errors:
            print(f"LLM errors: {dict(errors)}")
        print(f"Avg requirements/JD: {sum(n_reqs)/max(len(n_reqs),1):.1f}")
        print(f"Type distribution: {dict(types)}")
        print(f"Category distribution: {dict(cats)}")
        return

    if args.url:
        jd = descs.get(args.url, "")
        if not jd:
            print(f"ERROR: no cached JD for {args.url}")
            sys.exit(1)
        engine, err = extract_one(args.url, jd, cache, use_llm=not args.no_llm)
        n = len(cache[args.url]["requirements"])
        suffix = f" | llm_error: {err}" if err else ""
        print(f"{engine}: {n} requirements — {args.url}{suffix}")
        for r in cache[args.url]["requirements"][:10]:
            print(f"  [{r['type']:<9}] ({r['category']:<10}) {r['text'][:90]}")
        return

    # Batch mode: uncached JDs, bounded, parallel workers
    cap = args.backfill if args.backfill > 0 else 40
    todo_urls = [u for u, d in descs.items() if isinstance(d, str) and len(d) > 100 and u not in cache][:cap]
    workers = 1 if args.no_llm else MAX_WORKERS
    print(f"Extracting requirements for {len(todo_urls)} JD(s) "
          f"({'LLM: ' + MODEL + f', {MAX_WORKERS} workers' if not args.no_llm else 'heuristic only'})...")
    engines = Counter()
    errors = Counter()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extract_one, u, descs[u], cache, not args.no_llm): u for u in todo_urls}
        for fut in as_completed(futures):
            engine, err = fut.result()
            engines[engine] += 1
            if err:
                errors[err[:100]] += 1
            done += 1
            if done % 5 == 0 or done == len(todo_urls):
                print(f"  {done}/{len(todo_urls)} done (engines: {dict(engines)})", flush=True)
    print(f"Done. engines: {dict(engines)} | cache size: {len(cache)}")
    if errors:
        print("LLM errors (first 3):")
        for e, n in list(errors.items())[:3]:
            print(f"  {n}x {e}")


if __name__ == "__main__":
    main()