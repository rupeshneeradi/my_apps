"""
HireITPeople Resume Scraper
────────────────────────────────────────────────────────────────────────────
Fetches real bullet points from hireitpeople.com/resume-database that match
the JD's missing keywords. These become the "real examples from similar
professionals" shown alongside our template suggestions.

Design decisions:
  · Polite: max 4 resumes, 0.4 s delay between requests, 8 s timeout
  · Cached: same keyword-set results reused for 1 hour (in-process cache)
  · Graceful: any failure returns {} — app works without the scraper
  · Clean: strips nav/footer junk, only returns real experience bullets
"""

import re, time, logging, hashlib
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE    = "https://www.hireitpeople.com"
HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection":      "keep-alive",
}
TIMEOUT     = 8    # seconds per request
DELAY       = 0.4  # seconds between resume fetches
MAX_RESUMES = 4    # how many resumes to scrape per search
CACHE_TTL   = timedelta(hours=1)

# ── In-process cache ──────────────────────────────────────────────────────────
_cache: dict[str, tuple[datetime, dict]] = {}


# ── Category routing ──────────────────────────────────────────────────────────
# Maps sets of role-indicator keywords → HireITPeople category slug
_CATEGORY_RULES: list[tuple[set, str]] = [
    (
        {"oracle hcm", "hcm", "hcm extracts", "fast formula", "hdl",
         "hcm data loader", "oracle payroll", "payroll", "core hr",
         "absence management", "benefits", "hcm cloud", "fusion hcm"},
        "77-oracle-resumes",
    ),
    (
        {"informatica", "informatica powercenter", "datastage", "ibm datastage",
         "talend", "odi", "oracle data integrator", "etl", "goldengate",
         "data warehouse", "ssis", "pentaho"},
        "73-datawarehousing-etl-informatica-resumes",
    ),
    (
        {"oracle dba", "oracle rac", "oracle exadata", "data pump",
         "rman", "oracle database", "oracle 19c", "oracle 12c"},
        "78-oracle-dba-resumes",
    ),
    (
        {"oracle oic", "oic", "oracle integration cloud", "oracle soa",
         "soa suite", "bpel", "oracle mft", "rest adapter", "soap adapter"},
        "70-oracle-developers-resumes",
    ),
    (
        {"oracle apex", "apex", "ords", "application express",
         "oracle application express"},
        "70-oracle-developers-resumes",
    ),
    (
        {"netsuite", "suitescript", "suitelet", "restlet",
         "oracle netsuite", "netsuite erp"},
        "70-oracle-developers-resumes",
    ),
    (
        {"pl/sql", "plsql", "oracle forms", "oracle reports",
         "oracle ebs", "e-business suite", "oracle r12"},
        "70-oracle-developers-resumes",
    ),
    (
        {"oracle fusion", "oracle cloud", "oracle erp cloud",
         "fusion applications", "oracle adf", "adf", "vbcs"},
        "70-oracle-developers-resumes",
    ),
]
_DEFAULT_CATEGORY = "70-oracle-developers-resumes"


def _pick_category(keywords: list[str]) -> str:
    kw_set = {k.lower() for k in keywords}
    for rule_kws, slug in _CATEGORY_RULES:
        if kw_set & rule_kws:
            return slug
    return _DEFAULT_CATEGORY


# ── Listing page: collect resume URLs ────────────────────────────────────────

def _fetch_resume_urls(category: str) -> list[str]:
    url = f"{BASE}/resume-database/{category}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("Listing fetch failed (%s): %s", url, exc)
        return []

    seen, urls = set(), []
    # Use simple string matching — re.escape on https:// breaks the pattern
    pattern = rf'href="(https://www\.hireitpeople\.com/resume-database/{re.escape(category)}/[^"]+)"'
    for m in re.finditer(pattern, resp.text):
        href = m.group(1)
        if href not in seen:
            seen.add(href)
            urls.append(href)
    log.info("Found %d resume URLs in category %s", len(urls), category)
    return urls[:MAX_RESUMES * 2]   # fetch more so we have fallback if some fail


# ── Single resume page: extract bullets ──────────────────────────────────────

def _extract_resume_text(html: str) -> str:
    """Strip boilerplate, return clean resume text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "form", "iframe", "noscript"]):
        tag.decompose()
    # The resume body is usually inside a main content div
    body = soup.get_text(separator="\n")
    # Trim everything before SUMMARY or PROFESSIONAL EXPERIENCE
    for anchor in ("PROFESSIONAL EXPERIENCE", "SUMMARY", "EXPERIENCE"):
        idx = body.find(anchor)
        if idx != -1:
            body = body[idx:]
            break
    # Trim everything after cookie/footer noise
    for noise in ("Cookie", "Privacy Policy", "Copyright ©", "Hire IT People"):
        idx = body.find(noise)
        if idx != -1:
            body = body[:idx]
    return body


def _score_bullet(bullet: str, target_kws: list[str]) -> int:
    """Count how many target keywords appear in this bullet."""
    bl = bullet.lower()
    return sum(1 for kw in target_kws
               if re.search(r'\b' + re.escape(kw) + r'\b', bl))


def _extract_bullets_from_text(resume_text: str, target_kws: list[str]) -> list[str]:
    """
    Pull li-style or dash/dot-style bullet points that mention target keywords.
    Also pulls sentences from paragraph text that mention keywords.
    """
    results = []
    target_l = [kw.lower() for kw in target_kws]

    # Strategy 1: lines starting with common bullet markers
    for line in resume_text.splitlines():
        line = line.strip()
        # Typical resume bullets: starts with a letter (after stripping punctuation)
        if len(line) < 40 or len(line) > 600:
            continue
        if _score_bullet(line, target_l) == 0:
            continue
        # Skip section headers (all-caps short lines)
        if line.isupper() and len(line) < 60:
            continue
        results.append(line)

    return results


def _clean_bullet(text: str) -> str:
    """Normalise whitespace and capitalise first letter."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\-–•·▪◦▸►>]+\s*', '', text)
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:]
    return text


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_real_examples(
    missing_keywords: list[str],
    matched_keywords: list[str],
    max_per_keyword: int = 3,
) -> dict[str, list[str]]:
    """
    Return {missing_keyword: [bullet1, bullet2, ...]} scraped from
    real resumes on HireITPeople that are relevant to the JD.

    Falls back to {} on any network or parse error.
    """
    if not missing_keywords:
        return {}

    # ── Cache check ───────────────────────────────────────────────────────────
    cache_key = hashlib.md5(
        "|".join(sorted(missing_keywords)).encode()
    ).hexdigest()
    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if datetime.now() - ts < CACHE_TTL:
            log.info("Returning cached real examples (key=%s)", cache_key[:8])
            return cached

    all_kws    = missing_keywords + matched_keywords
    category   = _pick_category(all_kws)
    resume_urls= _fetch_resume_urls(category)

    results: dict[str, list[str]] = {kw: [] for kw in missing_keywords}
    fetched = 0

    for url in resume_urls:
        if fetched >= MAX_RESUMES:
            break
        # Stop early if we have enough examples for every keyword
        if all(len(v) >= max_per_keyword for v in results.values()):
            break

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resume_text = _extract_resume_text(resp.text)
            bullets     = _extract_bullets_from_text(resume_text, missing_keywords)

            for raw in bullets:
                cleaned = _clean_bullet(raw)
                if len(cleaned) < 40:
                    continue
                for kw in missing_keywords:
                    if (re.search(r'\b' + re.escape(kw.lower()) + r'\b', cleaned.lower())
                            and len(results[kw]) < max_per_keyword
                            and cleaned not in results[kw]):
                        results[kw].append(cleaned)

            fetched += 1
            log.info("Scraped resume %d/%d: %s", fetched, MAX_RESUMES, url.split("/")[-1])
            time.sleep(DELAY)

        except Exception as exc:
            log.warning("Resume scrape failed (%s): %s", url, exc)

    # Only return keywords that got at least one hit
    clean_results = {k: v for k, v in results.items() if v}
    _cache[cache_key] = (datetime.now(), clean_results)
    log.info("Real examples found for %d/%d missing keywords",
             len(clean_results), len(missing_keywords))
    return clean_results
