"""
Vendor pipeline — reads Vendor List.xlsx and searches LinkedIn for jobs
posted by each active vendor for all 8 job types (past 3 days).

Strategy: search LinkedIn with "JOB_TYPE VENDOR_NAME" to avoid running
one API call per vendor × per job type. Instead, for each job type we run
a broad LinkedIn search, then post-filter by vendor company names.

v1.0.4 — Replaced exact name matching with multi-token fuzzy matching:
  • Splits vendor & company names into word tokens (≥3 chars)
  • Match passes if ≥2 tokens overlap OR any single token ≥6 chars overlaps
  • Catches "TekSynap" vs "Teksynap Inc" and similar variations
"""
import hashlib
import logging
import re
import urllib.parse
from datetime import datetime, timezone

import openpyxl

from apify_pool import pool
from config import (
    ACTOR_LINKEDIN, VENDOR_DAYS_LOOKBACK, MAX_JOBS_PER_QUERY, SEARCH_QUERIES
)

log = logging.getLogger(__name__)

VENDOR_FILE = "Vendor List.xlsx"


def _load_vendors() -> list[dict]:
    wb = openpyxl.load_workbook(VENDOR_FILE)
    ws = wb.active
    vendors = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        name, url, status = row[0], row[1], row[2]
        if not name or not url:
            continue
        if status and "Working" in str(status):
            vendors.append({"name": str(name).strip(), "url": str(url).strip()})
    log.info("Loaded %d active vendors from %s", len(vendors), VENDOR_FILE)
    return vendors


def _linkedin_url(query: str, days: int = VENDOR_DAYS_LOOKBACK) -> str:
    seconds = days * 24 * 3600
    q = urllib.parse.quote_plus(query)
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={q}&f_TPR=r{seconds}&position=1&pageNum=0"
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _tokens(name: str) -> set[str]:
    """Return meaningful word tokens (≥3 chars) from a company name."""
    # Remove common suffixes that don't help matching
    name = re.sub(r"\b(inc|llc|ltd|corp|co|group|solutions|consulting|technologies|"
                  r"technology|services|staffing|systems|it|global|consulting)\b", "", name.lower())
    return {w for w in re.findall(r"[a-z0-9]+", name) if len(w) >= 3}


def _vendor_match(company_norm: str, vendor_tokens_list: list[set]) -> bool:
    """
    Return True if company_norm fuzzy-matches any vendor.
    Rules (OR):
      1. Exact substring match (original logic, catches 100% matches)
      2. ≥2 meaningful tokens overlap
      3. Any single token ≥6 chars overlaps (catches distinctive words like "teksynap")
    """
    comp_tokens = _tokens(company_norm)
    if not comp_tokens:
        return False
    for vt in vendor_tokens_list:
        overlap = comp_tokens & vt
        if overlap and (len(overlap) >= 2 or any(len(t) >= 6 for t in overlap)):
            return True
    return False


def _job_id(title: str, company: str, location: str) -> str:
    raw = f"{_normalize(title)}|{_normalize(company)}|{_normalize(location)}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _parse_item(item: dict, job_type: str, source: str = "vendor_linkedin") -> dict | None:
    title   = str(item.get("title", "") or "").strip()
    company = str(item.get("companyName", "") or item.get("company", "") or "").strip()
    loc     = str(item.get("location", "") or "").strip()
    # LinkedIn actor uses 'link'; others use 'jobUrl' or 'url'
    url     = str(item.get("link", "") or item.get("jobUrl", "") or item.get("url", "") or "").strip()
    desc    = str(item.get("descriptionText", "") or item.get("descriptionHtml", "") or item.get("description", "") or "").strip()
    posted  = str(item.get("postedAt", "") or item.get("postedDate", "") or "").strip()

    if not title or not url:
        return None

    return {
        "id":          _job_id(title, company, loc),
        "title":       title,
        "company":     company,
        "location":    loc,
        "url":         url,
        "description": re.sub(r"<[^>]+>", " ", desc),   # strip HTML
        "posted_date": posted,
        "scraped_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "portal":      source,
        "job_type":    job_type,
    }


def scrape_vendors() -> list[dict]:
    """Search LinkedIn for each job type and filter results by vendor company names."""
    vendors          = _load_vendors()
    vendor_set_norm  = {_normalize(v["name"]) for v in vendors}
    vendor_tokens_list = [_tokens(_normalize(v["name"])) for v in vendors]
    # Filter out empty token sets
    vendor_tokens_list = [vt for vt in vendor_tokens_list if vt]

    log.info("Vendor matching pool: %d vendors loaded", len(vendors))
    all_jobs: dict[str, dict] = {}   # id → job (deduplication)

    for job_type, queries in SEARCH_QUERIES.items():
        for query in queries[:1]:    # one primary query per job type
            url = _linkedin_url(query)
            log.info("Vendor scrape: %s → %s", query, url)
            try:
                items = pool.run_actor(
                    ACTOR_LINKEDIN,
                    {"urls": [url], "count": max(MAX_JOBS_PER_QUERY, 10), "scrapeCompany": False},
                    timeout_secs=180,
                )
            except Exception as exc:
                log.error("LinkedIn vendor scrape failed for %s: %s", query, exc)
                continue

            matched_count = 0
            for item in items:
                company_raw  = item.get("companyName", "") or item.get("company", "") or ""
                company_norm = _normalize(company_raw)

                # Layer 1: exact substring (original fast check)
                exact = any(v in company_norm or company_norm in v for v in vendor_set_norm)
                # Layer 2: token-based fuzzy match
                fuzzy = _vendor_match(company_norm, vendor_tokens_list)

                if not (exact or fuzzy):
                    continue

                job = _parse_item(item, job_type, source="vendor_linkedin")
                if job and job["id"] not in all_jobs:
                    all_jobs[job["id"]] = job
                    matched_count += 1
                    log.debug("  Vendor match: '%s' for %s", company_raw, job_type)

            log.info("  %s → %d vendor-matched jobs", query, matched_count)

    result = list(all_jobs.values())
    log.info("Vendor pipeline: %d unique jobs found", len(result))
    return result
