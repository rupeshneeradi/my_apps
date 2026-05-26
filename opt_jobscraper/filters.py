"""
Four-pass filter: OPT eligibility → defense contractor → relevance → seniority level.

v2 additions (P0 overhaul):
  • Defense company blocklist — blocks GDIT / Leidos / Booz Allen / etc.
  • Regex-based seniority detection — catches "Staff Fiber Network Engineer"
  • Non-IT industry signals — rejects manufacturing/automotive/telecom mismatches
  • Experience year extraction from JD body — hard-exclude "10+ years required"
"""
import logging
import re

from config import (
    ALL_DEVOPS_KEYWORDS,
    DEFENSE_COMPANY_BLOCKLIST,
    NON_IT_TITLE_SIGNALS,
    OPT_HARD_EXCLUDE, OPT_SOFT_EXCLUDE, OPT_POSITIVE,
    SENIOR_HARD_EXCLUDE, SENIOR_REGEX_PATTERNS, SENIOR_SOFT, ENTRY_MID_SIGNALS,
)

log = logging.getLogger(__name__)

# ── Pre-compiled regex patterns ───────────────────────────────────────────────

# Seniority regex: word-boundary patterns for senior-level detection
_SENIOR_RE: list[re.Pattern] = [
    re.compile(p, re.I) for p in SENIOR_REGEX_PATTERNS
]

# Experience year extractor — catches "8+ years", "10 years of experience", etc.
_EXP_YEAR_RE = re.compile(
    r'(\d+)\s*\+?\s*(?:to\s*\d+\s*)?years?(?:\s+of)?(?:\s+(?:experience|exp|relevant))?',
    re.I,
)
# Hard-exclude threshold: JD requires MORE than this many years → skip
_MAX_YEARS_OPT = 6   # OPT-friendly threshold (entry/mid-level ≤ 6 yrs)

# Non-tech business role signals in title
_NON_TECH_TITLE_SIGNALS = [
    "sales", "account executive", "account manager", "business development",
    "recruiter", "recruiting", "talent acquisition",
    "marketing", "product manager", "project manager", "program manager",
    "consultant manager", "practice manager", "delivery manager",
    "hr ", "human resources", "finance", "legal", "compliance officer",
    "customer success", "customer support", "solutions architect manager",
]

# At least one of these must appear in the title for the job to be kept
_TECH_TITLE_REQUIRED = [
    "devops", "dev ops", "cloud", "sre", "site reliability",
    "platform engineer", "infrastructure", "mlops", "devsecops",
    "kubernetes", "k8s", "ci/cd", "cicd",
    "linux", "systems engineer", "build engineer", "release engineer",
    "cloud security", "cloud architect", "cloud consultant",
    "aws engineer", "azure engineer", "gcp engineer",
    "network engineer", "cloud computing",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def _max_required_years(jd_text: str) -> int:
    """
    Extract the largest required-years number from a JD body.
    Returns 0 if no year requirement found.
    Scans only the first 2000 chars (the required section typically comes first).
    """
    snippet = jd_text[:2000].lower()
    # Only look at lines that suggest a requirement, not "5 years preferred"
    req_lines = []
    pref_mode = False
    for line in snippet.split("\n"):
        if re.search(r'\b(preferred|nice to have|plus|bonus|desired)\b', line, re.I):
            pref_mode = True
        elif re.search(r'\b(required|must have|mandatory|minimum)\b', line, re.I):
            pref_mode = False
        if not pref_mode:
            req_lines.append(line)

    req_text = " ".join(req_lines)
    years = [int(m.group(1)) for m in _EXP_YEAR_RE.finditer(req_text)]
    return max(years) if years else 0


# ── Individual filter checks ──────────────────────────────────────────────────

def check_opt(job: dict) -> tuple[bool, str, bool]:
    """Returns (pass, reason, is_opt_positive)."""
    full_text = _norm(f"{job['title']} {job.get('description', '')}")

    for term in OPT_HARD_EXCLUDE:
        if term in full_text:
            return False, f"OPT hard-exclude: '{term}'", False

    opt_positive = _contains_any(full_text, OPT_POSITIVE)
    return True, "OPT eligible", opt_positive


def check_defense_company(job: dict) -> tuple[bool, str]:
    """
    Reject jobs from known defense contractors that always require clearance.
    Fuzzy substring match on company name (case-insensitive).
    """
    company = (job.get("company") or "").lower().strip()
    if not company:
        return True, "Company unknown — skipping defense check"

    for blocked in DEFENSE_COMPANY_BLOCKLIST:
        if blocked in company:
            return False, f"Defense contractor blocked: '{company}' matches '{blocked}'"

    return True, "Company OK"


def check_relevance(job: dict) -> tuple[bool, str]:
    """
    Two-stage relevance check:
    1. Title must not be a non-tech business role or a non-IT industry role.
    2. Title must contain at least one DevOps/Cloud tech keyword.
    3. Description must contain at least 3 domain keywords.
    """
    title = _norm(job["title"])
    desc  = _norm(job.get("description", ""))

    # Hard reject generic non-tech business roles
    if _contains_any(title, _NON_TECH_TITLE_SIGNALS):
        return False, f"Non-tech title detected: '{job['title']}'"

    # Hard reject non-IT industry roles (manufacturing/automotive/telecom etc.)
    for signal in NON_IT_TITLE_SIGNALS:
        if signal in title:
            return False, f"Non-IT industry title: '{job['title']}' matches '{signal}'"

    # Title must contain at least one technical DevOps/Cloud keyword
    if not _contains_any(title, _TECH_TITLE_REQUIRED):
        return False, f"Title not DevOps/Cloud tech: '{job['title']}'"

    # Description must have at least 3 DevOps/Cloud keywords
    hits = sum(1 for kw in ALL_DEVOPS_KEYWORDS if kw in desc)
    if hits < 3:
        return False, f"Description too sparse ({hits} keyword hits)"

    return True, f"Relevant ({hits} keyword hits)"


def check_experience(job: dict) -> tuple[bool, str]:
    """
    Reject senior / leadership roles using both exact-string and regex patterns.
    Also rejects JDs that hard-require more than _MAX_YEARS_OPT years of experience.
    """
    title = _norm(job["title"])

    # Exact-string hard excludes (director, VP, head of, …)
    for term in SENIOR_HARD_EXCLUDE:
        if term in title:
            return False, f"Senior/leadership title (exact): '{term}'"

    # Regex-based seniority patterns — catches "Staff Fiber Network Engineer" etc.
    for pat in _SENIOR_RE:
        if pat.search(title):
            return False, f"Senior-level title (regex): '{pat.pattern}' in '{job['title']}'"

    # JD body experience-year check
    jd_text = job.get("description", "")
    if jd_text:
        max_yrs = _max_required_years(jd_text)
        if max_yrs > _MAX_YEARS_OPT:
            return False, f"Experience requirement too high: {max_yrs}+ years required"

    return True, "Experience level OK"


# ── Main filter pipeline ──────────────────────────────────────────────────────

def apply_filters(jobs: list[dict]) -> list[dict]:
    passed = []
    counts = {"opt": 0, "defense": 0, "relevance": 0, "experience": 0}

    for job in jobs:
        # Pass 1: OPT eligibility (citizenship / clearance / ITAR)
        ok, reason, opt_pos = check_opt(job)
        if not ok:
            counts["opt"] += 1
            log.debug("FILTER opt | %s | %s", job["title"], reason)
            continue

        # Pass 2: Defense contractor company check
        ok, reason = check_defense_company(job)
        if not ok:
            counts["defense"] += 1
            log.debug("FILTER defense | %s | %s", job.get("company","?"), reason)
            continue

        # Pass 3: Relevance (non-IT / non-tech / keyword density)
        ok, reason = check_relevance(job)
        if not ok:
            counts["relevance"] += 1
            log.debug("FILTER relevance | %s | %s", job["title"], reason)
            continue

        # Pass 4: Seniority / experience level
        ok, reason = check_experience(job)
        if not ok:
            counts["experience"] += 1
            log.debug("FILTER experience | %s | %s", job["title"], reason)
            continue

        job["opt_friendly"] = opt_pos
        passed.append(job)

    log.info(
        "Filters: %d passed | dropped opt=%d defense=%d relevance=%d experience=%d",
        len(passed), counts["opt"], counts["defense"], counts["relevance"], counts["experience"],
    )
    return passed
