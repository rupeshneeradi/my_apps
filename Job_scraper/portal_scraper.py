"""
Portal pipeline — scrapes LinkedIn, Indeed, Dice, Monster.
v1.0.8 changes:
  • _classify_job_type() now matches TITLE first, description second
    → fixes APEX jobs being bucketed as PL/SQL and Fusion Analysts as OIC
  • Added 2 targeted queries: APEX and Fusion Techno-Functional
    (5×4=20 Apify calls, covers all missed role types)

v1.0.7 changes:
  • Replaced description augmentation hack with c2c_search=True flag
  • Works with filters.py v1.0.7 HARD_EXCLUDE/SOFT_EXCLUDE/trust_portal logic

v1.0.6 changes:
  • Grouped queries: 3 broad searches × 4 portals = 12 Apify calls (was 32)
  • "c2c" added to all portal search queries → only C2C-tagged results fetched
  • Fixed Dice parser (detailsPageUrl, description_text, jobLocation.displayName)
  • MAX_JOBS_PER_QUERY reduced to 25 to save Apify tokens
  • classify_job_type() auto-assigns role from CORE_TITLE_TERMS
  • Cross-portal dedup by (company + normalized title)
"""
import hashlib
import logging
import re
import time
import urllib.parse
from datetime import datetime, timezone

from apify_pool import pool
from config import (
    ACTOR_DICE, ACTOR_INDEED, ACTOR_LINKEDIN, ACTOR_MONSTER,
    PORTAL_DAYS_LOOKBACK, MAX_JOBS_PER_QUERY, MONSTER_SEARCH_TMPL,
    CORE_TITLE_TERMS,
)

log = logging.getLogger(__name__)

# ── 5 C2C-specific queries covering all 8 job types ──────────────────────────
# 5×4=20 Apify calls. Extra APEX and Fusion/Techno-Functional queries added in
# v1.0.8 to fix roles that were missing from the top-25 "Oracle developer" results.
PORTAL_COMBINED_QUERIES = [
    "Oracle developer consultant c2c corp to corp",                # PL/SQL, HCM, OIC, Apps
    "Oracle APEX developer ords c2c corp to corp",                 # APEX Developer
    "Oracle Fusion techno functional analyst c2c corp to corp",    # Fusion ERP, Techno-Functional, Analyst roles
    "NetSuite consultant developer c2c corp to corp",              # NetSuite
    "ETL developer informatica data warehouse c2c",                # ETL / data
]

# Default job_type bucket per combined query (used if classify can't determine)
_QUERY_DEFAULT_TYPE = {
    "Oracle developer consultant c2c corp to corp":             "Oracle PL/SQL Developer",
    "Oracle APEX developer ords c2c corp to corp":              "Oracle Apex Developer",
    "Oracle Fusion techno functional analyst c2c corp to corp": "Oracle Fusion Developer",
    "NetSuite consultant developer c2c corp to corp":           "Oracle NetSuite Consultant",
    "ETL developer informatica data warehouse c2c":             "ETL Developer",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _job_id(title: str, company: str, location: str) -> str:
    raw = f"{_normalize(title)}|{_normalize(company)}|{_normalize(location)}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or ""))


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _classify_job_type(job: dict, default: str = "Oracle PL/SQL Developer") -> str:
    """
    Assign the correct job_type from CORE_TITLE_TERMS.

    Two-pass strategy (v1.0.8):
      Pass 1 — title only: if ANY term in CORE_TITLE_TERMS matches the title,
                use that job_type.  Title is ground-truth; description terms for
                OTHER role types must not override it.
      Pass 2 — full text: fall back to title+description scan for jobs whose
                title is generic (e.g. "IT Consultant", "Contract Developer").
    Returns default if nothing matches.
    """
    title = _normalize(job.get("title", ""))
    desc  = _normalize(job.get("description", ""))

    # Pass 1 — title-only match (highest priority)
    for jtype, terms in CORE_TITLE_TERMS.items():
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"\b", title):
                return jtype

    # Pass 2 — full text fallback
    full = title + " " + desc
    for jtype, terms in CORE_TITLE_TERMS.items():
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"\b", full):
                return jtype

    return default


def _title_key(title: str) -> str:
    """Normalize title for cross-portal dedup (strip seniority, location, etc.)"""
    t = title.lower()
    t = re.sub(r"\s*[\(\-–]\s*.*", "", t)
    for word in ("senior", "sr", "junior", "jr", "lead", "staff", "principal",
                 "associate", "remote", "contract", "temp", "consultant"):
        t = re.sub(r"\b" + word + r"\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _dedup_cross_portal(jobs: list[dict]) -> list[dict]:
    """Keep only one entry per (company + normalized_title), preferring longest description."""
    seen: dict[str, dict] = {}
    for j in jobs:
        key = f"{_normalize(j.get('company',''))}|{_title_key(j.get('title',''))}"
        if key not in seen:
            seen[key] = j
        elif len(j.get("description", "")) > len(seen[key].get("description", "")):
            seen[key] = j
    return list(seen.values())


# ── LinkedIn ──────────────────────────────────────────────────────────────────

def _linkedin_url(query: str) -> str:
    seconds = PORTAL_DAYS_LOOKBACK * 24 * 3600
    q = urllib.parse.quote_plus(query)
    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={q}&f_TPR=r{seconds}&position=1&pageNum=0"
    )


def scrape_linkedin(query: str, default_type: str) -> list[dict]:
    url = _linkedin_url(query)
    log.info("[LinkedIn] %s", query)
    try:
        items = pool.run_actor(
            ACTOR_LINKEDIN,
            {"urls": [url], "count": max(MAX_JOBS_PER_QUERY, 10), "scrapeCompany": False},
            timeout_secs=180,
        )
    except Exception as e:
        log.error("[LinkedIn] %s failed: %s", query, e)
        return []

    jobs = []
    for item in items:
        title   = str(item.get("title", "") or "").strip()
        company = str(item.get("companyName", "") or "").strip()
        loc     = str(item.get("location", "") or "").strip()
        url_    = str(item.get("link", "") or item.get("jobUrl", "") or "").strip()
        desc    = _strip_html(item.get("descriptionText", "") or item.get("descriptionHtml", ""))
        posted  = str(item.get("postedAt", "") or "").strip()
        if not title or not url_:
            continue
        job = {
            "id":           _job_id(title, company, loc),
            "title":        title,
            "company":      company,
            "location":     loc,
            "url":          url_,
            "description":  desc,
            "posted_date":  posted[:10],
            "scraped_date": _now_str(),
            "portal":       "LinkedIn",
            "job_type":     "",   # classified below
        }
        job["job_type"] = _classify_job_type(job, default_type)
        jobs.append(job)
    return jobs


# ── Indeed ────────────────────────────────────────────────────────────────────

def scrape_indeed(query: str, default_type: str) -> list[dict]:
    log.info("[Indeed] %s", query)
    try:
        items = pool.run_actor(
            ACTOR_INDEED,
            {
                "title":      query,
                "country":    "us",
                "limit":      MAX_JOBS_PER_QUERY,
                "datePosted": str(PORTAL_DAYS_LOOKBACK),
            },
            timeout_secs=180,
        )
    except Exception as e:
        log.error("[Indeed] %s failed: %s", query, e)
        return []

    jobs = []
    for item in items:
        title    = str(item.get("title", "") or "").strip()
        employer = item.get("employer") or {}
        company  = str(employer.get("name", "") or item.get("company", "") or "").strip()
        loc_obj  = item.get("location") or {}
        if isinstance(loc_obj, dict):
            city  = loc_obj.get("city", "") or ""
            state = loc_obj.get("admin1Code", "") or ""
            loc   = f"{city}, {state}".strip(", ")
        else:
            loc = str(loc_obj).strip()
        url_    = str(item.get("jobUrl", "") or item.get("url", "") or "").strip()
        desc    = _strip_html(item.get("description", "") or "")
        posted  = str(item.get("datePublished", "") or item.get("date", "") or "").strip()
        if not title or not url_:
            continue
        job = {
            "id":           _job_id(title, company, loc),
            "title":        title,
            "company":      company,
            "location":     loc,
            "url":          url_,
            "description":  desc,
            "posted_date":  posted[:10],
            "scraped_date": _now_str(),
            "portal":       "Indeed",
            "job_type":     "",
        }
        job["job_type"] = _classify_job_type(job, default_type)
        jobs.append(job)
    return jobs


# ── Dice ─────────────────────────────────────────────────────────────────────

def scrape_dice(query: str, default_type: str) -> list[dict]:
    log.info("[Dice] %s", query)
    try:
        items = pool.run_actor(
            ACTOR_DICE,
            {
                "keyword":        query,
                "location":       "USA",
                "posted_date":    "3d",
                "results_wanted": MAX_JOBS_PER_QUERY,
                "maxPages":       2,
            },
            timeout_secs=180,
        )
    except Exception as e:
        log.error("[Dice] %s failed: %s", query, e)
        return []

    jobs = []
    for item in items:
        title   = str(item.get("title", "") or "").strip()
        company = str(item.get("companyName", "") or item.get("company", "") or "").strip()

        # Dice returns jobLocation as a nested dict
        job_loc = item.get("jobLocation") or {}
        if isinstance(job_loc, dict):
            loc = str(job_loc.get("displayName", "") or
                      f"{job_loc.get('city','')}, {job_loc.get('state','')}".strip(", "))
        else:
            loc = str(job_loc).strip()

        # Correct field names confirmed from live API test
        url_   = str(item.get("detailsPageUrl", "") or item.get("url", "") or "").strip()
        desc   = _strip_html(item.get("description_text", "") or
                             item.get("description_html", "") or
                             item.get("summary", "") or "")
        posted = str(item.get("postedDate", "") or item.get("modifiedDate", "") or "").strip()

        if not title or not url_:
            continue
        job = {
            "id":           _job_id(title, company, loc),
            "title":        title,
            "company":      company,
            "location":     loc,
            "url":          url_,
            "description":  desc,
            "posted_date":  posted[:10],
            "scraped_date": _now_str(),
            "portal":       "Dice",
            "job_type":     "",
        }
        job["job_type"] = _classify_job_type(job, default_type)
        jobs.append(job)
    return jobs


# ── Monster ───────────────────────────────────────────────────────────────────

def scrape_monster(query: str, default_type: str) -> list[dict]:
    log.info("[Monster] %s", query)
    search_url = MONSTER_SEARCH_TMPL.format(query=urllib.parse.quote_plus(query))
    try:
        items = pool.run_actor(
            ACTOR_MONSTER,
            {"startUrls": [search_url], "maxItems": MAX_JOBS_PER_QUERY},
            timeout_secs=180,
        )
    except Exception as e:
        log.error("[Monster] %s failed: %s", query, e)
        return []

    jobs = []
    for item in items:
        jp      = item.get("jobPosting") or {}
        org     = jp.get("hiringOrganization") or {}
        locs    = jp.get("jobLocation") or [{}]
        addr    = (locs[0] or {}).get("address") or {}

        title   = str(jp.get("title", "") or item.get("title", "") or "").strip()
        company = str(org.get("name", "") or item.get("company", "") or "").strip()
        city    = str(addr.get("addressLocality", "") or "").strip()
        state   = str(addr.get("addressRegion", "") or "").strip()
        loc     = f"{city}, {state}".strip(", ") or str(item.get("location", "") or "").strip()
        url_    = str((item.get("apply") or {}).get("applyUrl", "") or item.get("url", "") or "").strip()
        desc    = _strip_html(jp.get("description", "") or item.get("description", "") or "")
        posted  = str(item.get("dateRecency", "") or item.get("formattedDate", "") or "").strip()

        if not title or not url_:
            continue
        job = {
            "id":           _job_id(title, company, loc),
            "title":        title,
            "company":      company,
            "location":     loc,
            "url":          url_,
            "description":  desc,
            "posted_date":  posted,
            "scraped_date": _now_str(),
            "portal":       "Monster",
            "job_type":     "",
        }
        job["job_type"] = _classify_job_type(job, default_type)
        jobs.append(job)
    return jobs


# ── Orchestrator ──────────────────────────────────────────────────────────────

def scrape_portals() -> list[dict]:
    """
    Run 3 combined C2C queries × 4 portals = 12 Apify calls (was 32).
    Each result is auto-classified into the correct job_type.
    """
    all_jobs: dict[str, dict] = {}

    scrapers = [
        ("LinkedIn", scrape_linkedin),
        ("Indeed",   scrape_indeed),
        ("Dice",     scrape_dice),
        ("Monster",  scrape_monster),
    ]

    # C2C terms embedded in our combined queries
    C2C_QUERY_TERMS = ["c2c", "corp to corp", "1099"]

    for query in PORTAL_COMBINED_QUERIES:
        default_type = _QUERY_DEFAULT_TYPE.get(query, "Oracle PL/SQL Developer")
        query_has_c2c = any(t in query.lower() for t in C2C_QUERY_TERMS)

        for portal_name, scraper_fn in scrapers:
            try:
                jobs = scraper_fn(query, default_type)

                # LinkedIn/Indeed/Dice return short descriptions that often omit "c2c".
                # Since we searched with c2c terms, mark these jobs as coming from a
                # c2c-targeted search — the filter will trust-pass them unless exclusion
                # language (W2, full-time, etc.) is found.
                if query_has_c2c and portal_name in ("LinkedIn", "Indeed", "Dice"):
                    for j in jobs:
                        j["c2c_search"] = True

                added = 0
                for j in jobs:
                    if j["id"] not in all_jobs:
                        all_jobs[j["id"]] = j
                        added += 1
                log.info("  %s / '%s' → %d jobs (%d new)", portal_name, query[:40], len(jobs), added)
            except Exception as exc:
                log.error("Scraper %s crashed: %s", portal_name, exc)
            time.sleep(2)   # polite delay

    result = list(all_jobs.values())
    log.info("Portal pipeline: %d jobs after primary dedup", len(result))

    result = _dedup_cross_portal(result)
    log.info("Portal pipeline: %d jobs after cross-portal dedup", len(result))
    return result
