"""
JD-driven ATS scorer — v1.0.9

How it works
────────────
1. JD KEYWORD EXTRACTION
   Scan the actual job description for every known technical term from a
   merged bank of ALL job-type keywords.  Only terms that appear in THIS
   specific JD are used for scoring — so the score reflects what this
   employer actually asked for, not a generic predefined list.

2. WEIGHTED SCORING
   • Terms in the JD title            → base weight × 2  (employer's top priority)
   • Multi-word phrases ("oracle apex", "hcm data loader") → base 2.0
   • Separator terms  ("pl/sql", "suitescript 2.0")        → base 1.5
   • Single words     ("apex", "informatica", "payroll")   → base 1.0
   score = Σ weight(matched) / Σ weight(all JD terms) × 100

3. RESUME MATCHING  (word-boundary regex, not substring)
   matched = JD keywords found in resume → already covered
   missing = JD keywords absent from resume → ADD THESE to boost ATS score

4. RESUME-TYPE PRIORITY
   Each job_type maps to a primary resume.  Primary wins if it scores
   within 10 points of the best — domain fit beats marginal score edge.

WHY THIS IS BETTER THAN v1.0.8
   v1.0.8 scored against a fixed predefined keyword list, reporting
   "missing" terms that the JD never mentioned.  v1.0.9 reports ONLY
   terms the JD itself contains — so every "missing" keyword is a direct
   recommendation to improve your resume for that specific posting.
"""
import re
import logging
from typing import NamedTuple

from config import JOB_TYPES, SCORE_LOW, SCORE_HIGH

log = logging.getLogger(__name__)

# ── Resume-type priority map ──────────────────────────────────────────────────
_PRIMARY_RESUME: dict[str, str] = {
    "oracle pl/sql developer":    "RoopeshN_sql.docx",
    "oracle hcm developer":       "Roopesh_HCM.docx",
    "oracle oic developer":       "Roopesh_OIC.docx",
    "oracle netsuite consultant": "R4_NetSuite_Consultant.docx",
    "oracle fusion developer":    "Roopesh_fusion.docx",
    "oracle apex developer":      "Roopesh_APEX.docx",
    "oracle apps developer":      "Roopesh_Apps.docx",
    "etl developer":              "Roopesh_ETL.docx",
}

_PRIORITY_TOLERANCE = 10.0  # primary wins within this many points of best

# ── Merged keyword bank (all job types, longest terms first for greedy scan) ──
_KEYWORD_BANK: list[str] = sorted(
    {kw for terms in JOB_TYPES.values() for kw in terms},
    key=lambda k: -len(k),   # match "informatica powercenter" before "informatica"
)

# ── Stopwords (not scored even if found in JD) ───────────────────────────────
_STOPWORDS = {
    "and", "or", "the", "a", "an", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "be", "will", "must", "have", "has",
    "been", "we", "our", "your", "you", "this", "that", "these",
    "those", "can", "may", "should", "would", "could", "not", "no",
    "as", "by", "from", "up", "about", "into", "through", "during",
    "including", "use", "using", "used", "work", "working", "experience",
    "years", "year", "strong", "good", "excellent", "preferred",
    "required", "ability", "skills", "skill", "knowledge", "team",
    "position", "role", "candidate", "responsibilities", "requirements",
    "qualifications", "minimum", "plus", "bachelor", "degree", "master",
    "certification", "etc", "also", "other", "related", "relevant",
}


class AtsResult(NamedTuple):
    score:       float       # 0–100 weighted score
    matched:     list[str]   # JD keywords found in resume
    missing:     list[str]   # JD keywords absent from resume (add these!)
    best_resume: str         # filename of recommended resume
    label:       str         # HOT / GOOD / OK / SKIP


# ── Helpers ───────────────────────────────────────────────────────────────────

def _term_weight(term: str) -> float:
    """Specificity-based base weight."""
    if " " in term:
        return 2.0   # multi-word phrase: "oracle apex", "hcm data loader"
    if any(c in term for c in "/.-_"):
        return 1.5   # separator term: "pl/sql", "suitescript 2.0"
    return 1.0       # single word


def _wb(term: str) -> re.Pattern:
    """Compile a word-boundary regex for a keyword (cached implicitly by Python)."""
    return re.compile(r"\b" + re.escape(term) + r"\b")


def _build_jd_profile(jd_text: str, jd_title: str) -> dict[str, float]:
    """
    Scan THIS job description for every known technical keyword.

    Returns {keyword: weight} — the 'requirement profile' of this JD.
    Only terms actually present in the JD are included, so every entry
    is something the employer genuinely mentioned.

    Title boost: keywords that also appear in the job title get 2× their
    base weight (they are the employer's headline requirements).
    """
    jd_lower    = jd_text.lower()
    title_lower = jd_title.lower()
    profile: dict[str, float] = {}

    for kw in _KEYWORD_BANK:
        # Skip if already captured as part of a longer phrase
        if any(kw in longer for longer in profile if len(longer) > len(kw)):
            continue
        if _wb(kw).search(jd_lower):
            w = _term_weight(kw)
            if _wb(kw).search(title_lower):
                w *= 2.0        # title boost
            profile[kw] = w

    return profile


# ── Core scoring ──────────────────────────────────────────────────────────────

def score_resume(
    resume_text: str,
    jd_text:     str,
    job_type:    str = "",     # kept for API compat; not used for keyword extraction
    jd_title:    str = "",
) -> tuple[float, list[str], list[str]]:
    """
    Score one resume against a job description.

    Returns (weighted_score%, matched_keywords, missing_keywords).

    matched = JD keywords present in resume   (already covered ✓)
    missing = JD keywords absent from resume  (add these to improve score)
    """
    profile = _build_jd_profile(jd_text, jd_title)
    if not profile:
        return 0.0, [], []

    resume_lower  = resume_text.lower()
    total_weight  = sum(profile.values())
    matched_w     = 0.0
    matched: list[str] = []
    missing: list[str] = []

    for kw, w in profile.items():
        if _wb(kw).search(resume_lower):
            matched.append(kw)
            matched_w += w
        else:
            missing.append(kw)

    score = (matched_w / total_weight) * 100 if total_weight else 0.0
    return round(score, 1), sorted(matched), sorted(missing)


def score_job(job: dict, resumes: dict[str, str]) -> AtsResult:
    """
    Score a job against all loaded resumes; return best match.

    Selection:
      1. Score every resume using the JD profile.
      2. Find the highest scorer.
      3. If the primary resume for this job_type is within
         _PRIORITY_TOLERANCE points, prefer it (domain fit > marginal gain).
    """
    job_type  = job.get("job_type", "")
    jd_text   = job.get("description", "") or ""
    jd_title  = job.get("title", "")        or ""

    if not resumes:
        return AtsResult(0.0, [], [], "No resumes loaded", "SKIP")

    # Score every resume
    results: dict[str, tuple[float, list, list]] = {
        fname: score_resume(rtext, jd_text, job_type, jd_title)
        for fname, rtext in resumes.items()
    }

    best_name  = max(results, key=lambda f: results[f][0])
    best_score = results[best_name][0]

    # Apply primary-resume priority
    primary = _PRIMARY_RESUME.get(job_type.lower(), "")
    chosen  = best_name
    if (primary
            and primary in results
            and results[primary][0] >= best_score - _PRIORITY_TOLERANCE):
        chosen = primary
        log.debug(
            "Resume priority: %s (%.1f) over %s (%.1f) for %s",
            primary, results[primary][0], best_name, best_score, job_type,
        )

    chosen_score, matched, missing = results[chosen]

    if chosen_score >= SCORE_HIGH:   label = "HOT"
    elif chosen_score >= 70:         label = "GOOD"
    elif chosen_score >= SCORE_LOW:  label = "OK"
    else:                            label = "SKIP"

    return AtsResult(chosen_score, matched, missing, chosen, label)
