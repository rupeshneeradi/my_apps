"""Domain-aware fallback ATS scorer for domains not covered by Job_scraper."""
from __future__ import annotations

import re

from role_classifier import DOMAINS


STOPWORDS = {
    "and", "or", "the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "be", "will", "must", "have", "has", "this", "that", "these",
    "those", "experience", "years", "year", "strong", "good", "excellent",
    "preferred", "required", "ability", "skills", "skill", "knowledge", "team",
    "position", "role", "candidate", "responsibilities", "requirements",
    "qualifications", "minimum", "plus", "degree", "related", "relevant",
}


SUPPORTED_EXTERNAL_DOMAINS = {
    "oracle_erp",
    "data_engineering",
    "devops_cloud",
    "software_dev",
    "cybersecurity",
    "database_admin",
    "non_it",
}


def _wb(term: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(term) + r"\b", re.I)


def _term_weight(term: str, title: str, source: str) -> float:
    if "title" == source:
        base = 4.0
    elif "primary" == source:
        base = 3.0
    elif "secondary" == source:
        base = 1.25
    else:
        base = 1.0
    if " " in term:
        base += 0.75
    if any(c in term for c in "/.-_"):
        base += 0.35
    if _wb(term).search(title):
        base *= 2.0
    return base


def score_with_domain_bank(
    resume_text: str,
    jd_text: str,
    jd_title: str,
    domain: str,
) -> tuple[float, list[str], list[str]]:
    """Score using role_classifier domain vocab when external bank is missing."""
    cfg = DOMAINS.get(domain)
    if not cfg:
        return 0.0, [], []

    jd = jd_text.lower()
    title = jd_title.lower()
    candidates: dict[str, float] = {}

    for source in ("titles", "primary", "secondary"):
        source_name = "title" if source == "titles" else source
        for kw in cfg.get(source, []):
            if kw in STOPWORDS:
                continue
            if _wb(kw).search(jd) or _wb(kw).search(title):
                candidates[kw] = max(candidates.get(kw, 0.0), _term_weight(kw, title, source_name))

    if not candidates:
        return 0.0, [], []

    resume = resume_text.lower()
    total = sum(candidates.values())
    matched_weight = 0.0
    matched: list[str] = []
    missing: list[str] = []

    for kw, weight in candidates.items():
        if _wb(kw).search(resume):
            matched.append(kw)
            matched_weight += weight
        else:
            missing.append(kw)

    return round((matched_weight / total) * 100, 1), sorted(matched), sorted(missing)
