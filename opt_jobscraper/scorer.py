"""Score each job 0–100 for OPT DevOps fit."""
import logging
import re
from datetime import datetime, timezone

from config import (
    ALL_DEVOPS_KEYWORDS, JOB_TYPES,
    OPT_POSITIVE, OPT_SOFT_EXCLUDE,
    ENTRY_MID_SIGNALS, SENIOR_SOFT,
    SCORE_WEIGHTS,
)

log = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _hit_count(text: str, terms) -> int:
    return sum(1 for t in terms if t in text)


def score_job(job: dict) -> int:
    title = _norm(job.get("title", ""))
    desc  = _norm(job.get("description", ""))
    full  = title + " " + desc
    score = 0

    if _hit_count(full, OPT_POSITIVE) > 0:
        score += SCORE_WEIGHTS["opt_positive"]

    if _hit_count(full, OPT_SOFT_EXCLUDE) > 0:
        score += SCORE_WEIGHTS["opt_soft_exclude"]

    if _hit_count(full, ENTRY_MID_SIGNALS) > 0:
        score += SCORE_WEIGHTS["entry_mid_signal"]

    if _hit_count(full, SENIOR_SOFT) > 0:
        score += SCORE_WEIGHTS["senior_soft"]

    if job.get("is_remote") or _hit_count(full, ["remote", "hybrid", "work from home"]) > 0:
        score += SCORE_WEIGHTS["remote"]

    job_type     = job.get("job_type", "")
    type_keywords = JOB_TYPES.get(job_type, list(ALL_DEVOPS_KEYWORDS))
    hits         = _hit_count(desc, type_keywords)
    max_hits     = min(len(type_keywords), 20)
    score += int(SCORE_WEIGHTS["keyword_depth"] * min(hits / max(max_hits, 1), 1.0))

    posted = job.get("posted_date", "")
    if posted:
        try:
            d = datetime.strptime(posted, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - d).days < 1:
                score += SCORE_WEIGHTS["recency"]
        except ValueError:
            pass

    if len(desc) > 500:
        score += SCORE_WEIGHTS["description_len"]

    return max(0, min(score, 100))


def score_all(jobs: list[dict]) -> list[dict]:
    for job in jobs:
        job["score"] = score_job(job)
    jobs.sort(key=lambda j: j["score"], reverse=True)
    if jobs:
        log.info("Scorer: top=%d avg=%.0f min=%d",
                 jobs[0]["score"],
                 sum(j["score"] for j in jobs) / len(jobs),
                 jobs[-1]["score"])
    return jobs
