"""Evidence-based resume/JD evaluator.

This layer keeps the existing deterministic ATS keyword score, but adds a
structured rubric that behaves more like a careful resume reviewer:
requirements are scored by priority, matched skills need resume evidence, and
rewrite guidance separates safe additions from learning gaps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from role_classifier import classify, domain_label, role_fit


REQUIRED_SIGNAL = re.compile(
    r"\b(required|must have|must-have|mandatory|minimum|required qualifications|requirements)\b",
    re.I,
)
PREFERRED_SIGNAL = re.compile(
    r"\b(preferred|nice to have|nice-to-have|plus|bonus|desired|good to have|advantage)\b",
    re.I,
)
SECTION_HEADING = re.compile(
    r"^\s*(summary|profile|objective|skills|technical skills|technologies|experience|"
    r"professional experience|work experience|employment|projects|education|certifications?)\s*:?\s*$",
    re.I,
)
METRIC_RE = re.compile(
    r"\b\d{1,3}[%+]"
    r"|\$\s*\d[\d,kKmMbB]+"
    r"|\b\d+\s*(year|month|client|project|user|system|team|interface|integration|module|report|screen)s?\b",
    re.I,
)
YEARS_RE = re.compile(r"(\d{1,2})\+?\s*years?", re.I)


@dataclass(frozen=True)
class ResumeSection:
    name: str
    lines: list[str]


def _keyword_re(keyword: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.I)


def _clip(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def split_resume_sections(resume_text: str) -> list[ResumeSection]:
    """Best-effort resume section splitter for plain text extracted from docs."""
    sections: list[ResumeSection] = []
    current = "unknown"
    lines: list[str] = []

    for raw in resume_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = SECTION_HEADING.match(line)
        if heading:
            if lines:
                sections.append(ResumeSection(current, lines))
            current = heading.group(1).lower()
            lines = []
            continue
        lines.append(line)

    if lines:
        sections.append(ResumeSection(current, lines))
    return sections or [ResumeSection("unknown", [resume_text])]


def jd_priority_profile(jd_text: str, jd_title: str, keywords: list[str]) -> dict[str, str]:
    """Classify scored keywords as title, required, preferred, or mentioned."""
    title = jd_title.lower()
    mode = "required"
    buckets = {"required": "", "preferred": ""}
    for raw in jd_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if PREFERRED_SIGNAL.search(line):
            mode = "preferred"
        elif REQUIRED_SIGNAL.search(line):
            mode = "required"
        buckets[mode] += " " + line.lower()

    profile: dict[str, str] = {}
    for kw in keywords:
        rx = _keyword_re(kw)
        if rx.search(title):
            profile[kw] = "title"
        elif rx.search(buckets["required"]):
            profile[kw] = "required"
        elif rx.search(buckets["preferred"]):
            profile[kw] = "preferred"
        else:
            profile[kw] = "mentioned"
    return profile


def find_keyword_evidence(resume_text: str, keywords: list[str]) -> dict[str, dict]:
    """Map matched keywords to resume evidence lines and evidence quality."""
    sections = split_resume_sections(resume_text)
    evidence: dict[str, dict] = {}

    for kw in keywords:
        rx = _keyword_re(kw)
        hits = []
        best = "none"
        for section in sections:
            section_name = section.name
            for line in section.lines:
                if not rx.search(line):
                    continue
                has_metric = bool(METRIC_RE.search(line))
                if "skill" in section_name or "technolog" in section_name:
                    level = "listed"
                elif any(s in section_name for s in ("experience", "work", "employment", "project")):
                    level = "proven_with_metric" if has_metric else "proven"
                else:
                    level = "mentioned"

                rank = {"none": 0, "mentioned": 1, "listed": 2, "proven": 3, "proven_with_metric": 4}
                if rank[level] > rank[best]:
                    best = level
                hits.append({
                    "section": section_name,
                    "line": _clip(line),
                    "has_metric": has_metric,
                    "level": level,
                })

        if hits:
            evidence[kw] = {"level": best, "hits": hits[:3]}
    return evidence


def _coverage_score(total: list[str], matched: set[str], fallback: float) -> int:
    if not total:
        return round(fallback)
    return round((sum(1 for kw in total if kw in matched) / len(total)) * 100)


def _seniority_score(resume_text: str, jd_text: str, fit_score: int) -> tuple[int, dict]:
    resume_years = max((int(x) for x in YEARS_RE.findall(resume_text)), default=0)
    jd_years = max((int(x) for x in YEARS_RE.findall(jd_text)), default=0)
    if not jd_years:
        years_score = 80 if resume_years else 65
    elif resume_years >= jd_years:
        years_score = 100
    elif resume_years:
        years_score = max(35, round((resume_years / jd_years) * 100))
    else:
        years_score = 45
    score = round((fit_score * 0.65) + (years_score * 0.35))
    return score, {"resume_years": resume_years, "jd_years": jd_years, "years_score": years_score}


def _formatting_score(sections: dict[str, bool]) -> int:
    score = 40
    score += 20 if sections.get("summary") else 0
    score += 20 if sections.get("skills") else 0
    score += 15 if sections.get("experience") else 0
    score += 5 if sections.get("education") else 0
    return min(100, score)


def _confidence(score: int, evidence_count: int, total_keywords: int) -> str:
    if total_keywords < 3:
        return "low"
    if evidence_count >= max(2, total_keywords // 3) and score >= 65:
        return "high"
    return "medium"


def evaluate_resume_fit(
    resume_text: str,
    jd_text: str,
    jd_title: str,
    ats_score: float,
    quality_score: int,
    matched: list[str],
    missing: list[str],
    sections: dict[str, bool],
) -> dict:
    all_keywords = sorted(set(matched) | set(missing))
    matched_set = set(matched)
    priority = jd_priority_profile(jd_text, jd_title, all_keywords)
    evidence = find_keyword_evidence(resume_text, matched)

    jd_domain, jd_confidence, _ = classify((jd_title + "\n" + jd_text).strip())
    resume_domain, resume_confidence, _ = classify(resume_text)
    fit_score = role_fit(resume_domain, jd_domain)
    seniority_score, seniority = _seniority_score(resume_text, jd_text, fit_score)

    required_terms = [kw for kw, p in priority.items() if p in ("title", "required")]
    preferred_terms = [kw for kw, p in priority.items() if p == "preferred"]
    mentioned_terms = [kw for kw, p in priority.items() if p == "mentioned"]

    required_score = _coverage_score(required_terms, matched_set, ats_score)
    preferred_score = _coverage_score(preferred_terms, matched_set, ats_score)
    if not preferred_terms and mentioned_terms:
        preferred_score = _coverage_score(mentioned_terms, matched_set, ats_score)

    evidence_points = []
    for kw in matched:
        level = evidence.get(kw, {}).get("level", "none")
        evidence_points.append({
            "none": 0,
            "mentioned": 35,
            "listed": 55,
            "proven": 80,
            "proven_with_metric": 100,
        }.get(level, 0))
    evidence_score = round(sum(evidence_points) / len(evidence_points)) if evidence_points else 0

    impact_score = min(100, 35 + len(METRIC_RE.findall(resume_text)) * 8)
    formatting_score = _formatting_score(sections)

    weights = {
        "required_skills": 0.30,
        "preferred_skills": 0.15,
        "evidence_strength": 0.15,
        "role_seniority_match": 0.10,
        "resume_quality": 0.10,
        "ats_formatting": 0.10,
        "impact_quantification": 0.10,
    }
    raw_scores = {
        "required_skills": required_score,
        "preferred_skills": preferred_score,
        "evidence_strength": evidence_score,
        "role_seniority_match": seniority_score,
        "resume_quality": quality_score,
        "ats_formatting": formatting_score,
        "impact_quantification": impact_score,
    }
    overall = round(sum(raw_scores[k] * weights[k] for k in weights))

    safe_to_add = []
    learning_gaps = []
    for kw in missing:
        related = [
            hit for hit in matched
            if kw in hit or hit in kw
        ]
        item = {"keyword": kw, "priority": priority.get(kw, "mentioned"), "related_evidence": related[:3]}
        if related:
            safe_to_add.append(item)
        else:
            learning_gaps.append(item)

    categories = [
        {
            "key": key,
            "label": label,
            "score": raw_scores[key],
            "weight": round(weights[key] * 100),
            "reason": reason,
            "confidence": _confidence(raw_scores[key], len(evidence), len(all_keywords)),
        }
        for key, label, reason in [
            ("required_skills", "Required skills", "Coverage of title and required JD terms."),
            ("preferred_skills", "Preferred skills", "Coverage of preferred or lower-priority JD terms."),
            ("evidence_strength", "Evidence strength", "Whether skills are proven in resume bullets, not just listed."),
            ("role_seniority_match", "Role/seniority match", "Domain compatibility plus years-of-experience alignment."),
            ("resume_quality", "Resume quality", "Sections, action language, metrics, and weak phrasing."),
            ("ats_formatting", "ATS formatting", "Core resume sections that parsers expect."),
            ("impact_quantification", "Impact/metrics", "Measurable business or technical outcomes in bullets."),
        ]
    ]

    return {
        "overall_score": overall,
        "categories": categories,
        "keyword_priority": priority,
        "evidence": evidence,
        "safe_to_add": safe_to_add[:12],
        "learning_gaps": learning_gaps[:12],
        "domains": {
            "jd": {"key": jd_domain, "label": domain_label(jd_domain), "confidence": jd_confidence},
            "resume": {"key": resume_domain, "label": domain_label(resume_domain), "confidence": resume_confidence},
            "fit_score": fit_score,
        },
        "seniority": seniority,
        "verification_summary": {
            "required_total": len(required_terms),
            "required_matched": sum(1 for kw in required_terms if kw in matched_set),
            "preferred_total": len(preferred_terms),
            "preferred_matched": sum(1 for kw in preferred_terms if kw in matched_set),
            "evidence_backed_keywords": len(evidence),
            "total_scored_keywords": len(all_keywords),
        },
    }


def verdict_from_score(score: int, required_score: int) -> tuple[str, str, str]:
    if score >= 80 and required_score >= 75:
        return "STRONG FIT", "hot", "High"
    if score >= 65 and required_score >= 55:
        return "GOOD FIT", "good", "Medium"
    if score >= 45:
        return "POSSIBLE", "ok", "Low"
    return "NOT A FIT", "skip", "Very Low"
