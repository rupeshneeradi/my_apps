"""Scrape job portals using python-jobspy."""
import logging
import re
import hashlib
from datetime import datetime, timezone

import pandas as pd
from jobspy import scrape_jobs

from config import (
    PORTALS, RESULTS_PER_QUERY, DAYS_LOOKBACK,
    COUNTRY, LOCATION, SEARCH_QUERIES,
)

log = logging.getLogger(__name__)


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _job_id(title: str, company: str, location: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _clean(text) -> str:
    if pd.isna(text) or text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or ""))


def _posted_date(date_val) -> str:
    if pd.isna(date_val) or date_val is None:
        return ""
    if isinstance(date_val, datetime):
        return date_val.strftime("%Y-%m-%d")
    return str(date_val)[:10]


def _is_recent(posted: str, days: int = DAYS_LOOKBACK) -> bool:
    if not posted:
        return True
    try:
        d = datetime.strptime(posted, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days <= days
    except ValueError:
        return True


def scrape_query(job_type: str, query: str, portals: list[str] = PORTALS) -> list[dict]:
    log.info("[scrape] '%s' on %s", query, portals)
    try:
        df = scrape_jobs(
            site_name=portals,
            search_term=query,
            location=LOCATION,
            results_wanted=RESULTS_PER_QUERY,
            hours_old=DAYS_LOOKBACK * 24,
            country_indeed=COUNTRY,
            linkedin_fetch_description=True,
        )
    except Exception as exc:
        log.error("[scrape] query='%s' failed: %s", query, exc)
        return []

    jobs = []
    for _, row in df.iterrows():
        title   = _clean(row.get("title"))
        company = _clean(row.get("company"))
        loc     = _clean(row.get("location"))
        url     = _clean(row.get("job_url"))
        desc    = _strip_html(_clean(row.get("description")))
        posted  = _posted_date(row.get("date_posted"))
        portal  = _clean(row.get("site", ""))
        remote  = str(row.get("is_remote", "")).lower() == "true"
        emp_type = _clean(row.get("job_type", ""))

        if not title or not url:
            continue
        if not _is_recent(posted):
            continue

        jobs.append({
            "id":           _job_id(title, company, loc),
            "title":        title,
            "company":      company,
            "location":     loc,
            "url":          url,
            "description":  desc,
            "posted_date":  posted,
            "scraped_date": _now_str(),
            "portal":       portal,
            "job_type":     job_type,
            "is_remote":    remote,
            "emp_type":     emp_type,
            "score":        0,
            "opt_friendly": None,
        })

    log.info("  '%s' → %d jobs", query[:50], len(jobs))
    return jobs


def scrape_all() -> list[dict]:
    seen: dict[str, dict] = {}

    for job_type, queries in SEARCH_QUERIES.items():
        for query in queries:
            results = scrape_query(job_type, query)
            for job in results:
                jid = job["id"]
                if jid not in seen:
                    seen[jid] = job
                elif len(job["description"]) > len(seen[jid]["description"]):
                    seen[jid] = job

    all_jobs = list(seen.values())
    log.info("Scraper: %d unique jobs after dedup", len(all_jobs))
    return all_jobs
