"""Three-pass filter: OPT eligibility → DevOps relevance → experience level."""
import logging
import re

from config import (
    ALL_DEVOPS_KEYWORDS,
    OPT_HARD_EXCLUDE, OPT_SOFT_EXCLUDE, OPT_POSITIVE,
    SENIOR_HARD_EXCLUDE, SENIOR_SOFT, ENTRY_MID_SIGNALS,
)

log = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def check_opt(job: dict) -> tuple[bool, str, bool]:
    """Returns (pass, reason, is_opt_positive)."""
    full_text = _norm(f"{job['title']} {job['description']}")

    for term in OPT_HARD_EXCLUDE:
        if term in full_text:
            return False, f"OPT hard-exclude: '{term}'", False

    opt_positive = _contains_any(full_text, OPT_POSITIVE)
    return True, "OPT eligible", opt_positive


# Titles that look technical but are NOT engineering roles
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


def check_relevance(job: dict) -> tuple[bool, str]:
    title = _norm(job["title"])
    desc  = _norm(job["description"])

    # Hard reject non-tech roles even if title has "cloud" or "devops" in suffix
    if _contains_any(title, _NON_TECH_TITLE_SIGNALS):
        return False, f"Non-tech title detected: '{job['title']}'"

    # Title must contain at least one technical role keyword
    if not _contains_any(title, _TECH_TITLE_REQUIRED):
        return False, f"Title not tech DevOps/Cloud: '{job['title']}'"

    # Description must have at least 3 DevOps/Cloud keywords (raised from 2)
    hits = sum(1 for kw in ALL_DEVOPS_KEYWORDS if kw in desc)
    if hits < 3:
        return False, f"Description too sparse ({hits} keyword hits)"

    return True, f"Relevant ({hits} keyword hits)"


def check_experience(job: dict) -> tuple[bool, str]:
    title = _norm(job["title"])

    for term in SENIOR_HARD_EXCLUDE:
        if term in title:
            return False, f"Senior/leadership title: '{term}'"

    return True, "Experience level OK"


def apply_filters(jobs: list[dict]) -> list[dict]:
    passed = []
    counts = {"opt": 0, "relevance": 0, "experience": 0}

    for job in jobs:
        ok, reason, opt_pos = check_opt(job)
        if not ok:
            counts["opt"] += 1
            log.debug("FILTER opt | %s | %s", job["title"], reason)
            continue

        ok, reason = check_relevance(job)
        if not ok:
            counts["relevance"] += 1
            log.debug("FILTER relevance | %s | %s", job["title"], reason)
            continue

        ok, reason = check_experience(job)
        if not ok:
            counts["experience"] += 1
            log.debug("FILTER experience | %s | %s", job["title"], reason)
            continue

        job["opt_friendly"] = opt_pos
        passed.append(job)

    log.info(
        "Filters: %d passed | dropped opt=%d relevance=%d experience=%d",
        len(passed), counts["opt"], counts["relevance"], counts["experience"],
    )
    return passed
