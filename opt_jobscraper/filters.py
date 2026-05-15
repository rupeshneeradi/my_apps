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


def check_relevance(job: dict) -> tuple[bool, str]:
    title = _norm(job["title"])
    desc  = _norm(job["description"])

    TITLE_MUST_HAVE = [
        "devops", "cloud", "sre", "reliability", "platform", "infrastructure",
        "mlops", "devsecops", "kubernetes", "k8s", "ci/cd", "cicd",
        "systems engineer", "linux engineer", "build engineer", "release engineer",
        "security engineer", "network engineer",
    ]
    if not _contains_any(title, TITLE_MUST_HAVE):
        return False, f"Title not DevOps-related: '{job['title']}'"

    hits = sum(1 for kw in ALL_DEVOPS_KEYWORDS if kw in desc)
    if hits < 2:
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
