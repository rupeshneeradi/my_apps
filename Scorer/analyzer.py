"""
Rule-based recruiter-level resume analyzer.
No AI / API / external calls — 100% deterministic, instant, free.

Dimensions evaluated:
  1. ATS keyword match (from ats_scorer)
  2. Resume quality signals (quantification, action verbs, sections)
  3. JD requirement priority (required vs preferred)
  4. Gap criticality (title-level > required > preferred)
  5. Verdict + interview-chance + ranked improvement plan
"""
import re
from dataclasses import dataclass, field

# ── Signal vocabulary ─────────────────────────────────────────────────────────

STRONG_VERBS = {
    "implemented","architected","designed","led","built","developed","created",
    "delivered","improved","reduced","increased","managed","deployed","migrated",
    "integrated","optimized","streamlined","established","launched","spearheaded",
    "drove","transformed","configured","customized","automated","resolved",
    "troubleshot","debugged","analyzed","evaluated","conducted","executed",
    "coordinated","facilitated","trained","mentored","engineered","enhanced",
    "standardized","upgraded","consolidated","accelerated","introduced","handled",
}

WEAK_PHRASES = [
    "responsible for","helped with","assisted","involved in",
    "participated in","duties included","worked on","contributed to",
]

_STRONG_RE  = re.compile(r'\b(' + '|'.join(re.escape(v) for v in STRONG_VERBS) + r')\b', re.I)
_WEAK_RE    = re.compile('(' + '|'.join(re.escape(p) for p in WEAK_PHRASES) + ')', re.I)

# metrics: "30%", "8 years", "$2M", "50+ users", "3 systems", "12 clients"
_METRIC_RE  = re.compile(
    r'\b\d{1,3}[%+]'
    r'|\$\s*\d[\d,kKmMbB]+'
    r'|\b\d+\s*(year|month|client|project|user|system|team|interface|integration|module|report|screen)s?\b',
    re.I
)

_YEARS_RE   = re.compile(r'(\d{1,2})\+?\s*years?\s*(of\s*)?(experience|exp\.?)', re.I)
_VERSION_RE = re.compile(
    r'\b(r12|11\.5|12\.1|12\.2|11g|12c|19c|21c|apex\s*2[0-9]|apex\s*[0-9]+|'
    r'suitescript\s*[0-9.]+|oracle\s*[0-9]+|oic\s*[0-9]+)\b', re.I
)

SECTION_PATTERNS = {
    "summary":        r'\b(summary|profile|objective|overview|about me|professional summary)\b',
    "skills":         r'\b(skills|technical skills|technologies|tech stack|tools|competencies|core competencies)\b',
    "experience":     r'\b(experience|employment|work history|career history|professional experience)\b',
    "education":      r'\b(education|degree|university|college|bachelor|master|b\.?e\.?|b\.?tech|m\.?tech)\b',
    "certifications": r'\b(certif|certified|oracle certified|ocp|oce|oca|credential)\b',
}

# ── JD parser ─────────────────────────────────────────────────────────────────

_REQUIRED_SIGNAL  = re.compile(r'\b(required|must have|must-have|mandatory|minimum|key requirement)\b', re.I)
_PREFERRED_SIGNAL = re.compile(r'\b(preferred|nice to have|nice-to-have|plus|bonus|desired|good to have|advantage)\b', re.I)


def _jd_priority_texts(jd_text: str) -> dict[str, str]:
    """Split JD lines into 'required' and 'preferred' buckets."""
    req, pref = [], []
    mode = "required"
    for line in jd_text.split("\n"):
        if _PREFERRED_SIGNAL.search(line):
            mode = "preferred"
        elif _REQUIRED_SIGNAL.search(line):
            mode = "required"
        if mode == "required":
            req.append(line.lower())
        else:
            pref.append(line.lower())
    return {"required": " ".join(req), "preferred": " ".join(pref)}


def _keyword_in(kw: str, text: str) -> bool:
    return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))


# ── Quality scorer ────────────────────────────────────────────────────────────

def _quality_score(strong_v: int, weak_v: int, metrics: int, sections: dict) -> int:
    score = 40
    score += 10 if sections["summary"]        else 0
    score +=  8 if sections["skills"]         else 0
    score +=  5 if sections["experience"]     else 0
    score +=  7 if sections["certifications"] else 0
    score += min(metrics * 3, 18)   # each measurable result adds 3pts, cap 18
    score += min(strong_v * 2, 12)  # strong verbs
    score -= min(weak_v  * 3, 15)   # penalty for passive language
    return max(0, min(100, score))


# ── Main entry ────────────────────────────────────────────────────────────────

def analyze(
    resume_text: str,
    resume_name: str,
    jd_text: str,
    jd_title: str,
    ats_score: float,
    matched: list[str],
    missing: list[str],
) -> dict:
    """
    Return a full recruiter-level analysis dict.
    Combines ATS keyword data with resume quality signals.
    """
    tl = resume_text.lower()
    title_l = jd_title.lower()

    # ── Resume signals ────────────────────────────────────────────────────────
    strong_v  = len(set(_STRONG_RE.findall(resume_text)))
    weak_v    = len(_WEAK_RE.findall(tl))
    metrics   = len(_METRIC_RE.findall(resume_text))
    versions  = list({v[0].lower() for v in _VERSION_RE.findall(resume_text)})
    years_m   = _YEARS_RE.findall(resume_text)
    max_years = max((int(y[0]) for y in years_m), default=0)
    sections  = {k: bool(re.search(v, tl)) for k, v in SECTION_PATTERNS.items()}
    quality   = _quality_score(strong_v, weak_v, metrics, sections)

    # ── Gap priority breakdown ────────────────────────────────────────────────
    prio = _jd_priority_texts(jd_text)
    critical  = [k for k in missing if _keyword_in(k, title_l)]
    required  = [k for k in missing if k not in critical and _keyword_in(k, prio["required"])]
    preferred = [k for k in missing if k not in critical and k not in required]

    # ── Recruiter composite score ─────────────────────────────────────────────
    # 55% keyword match + 45% resume quality
    rec_score = round(ats_score * 0.55 + quality * 0.45)

    # ── Verdict ──────────────────────────────────────────────────────────────
    if rec_score >= 75 and not critical:
        verdict, vcolor, interview = "STRONG FIT", "hot",  "High"
    elif rec_score >= 60:
        verdict, vcolor, interview = "GOOD FIT",   "good", "Medium"
    elif rec_score >= 40:
        verdict, vcolor, interview = "POSSIBLE",   "ok",   "Low"
    else:
        verdict, vcolor, interview = "NOT A FIT",  "skip", "Very Low"

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths = []
    if ats_score >= 80:
        strengths.append(f"Strong keyword alignment — {ats_score}% of JD keywords found")
    elif ats_score >= 60:
        strengths.append(f"Decent keyword match ({ats_score}%) — above average for ATS filter")
    if max_years >= 7:
        strengths.append(f"Deep experience depth — {max_years}+ years mentioned in resume")
    elif max_years >= 3:
        strengths.append(f"Relevant experience level — {max_years}+ years mentioned")
    if metrics >= 6:
        strengths.append(f"Well-quantified impact — {metrics} measurable results found")
    elif metrics >= 3:
        strengths.append(f"Some quantified results — {metrics} metrics found (add more)")
    if strong_v >= 7:
        strengths.append(f"Strong action language — {strong_v} power verbs used")
    if sections["certifications"]:
        strengths.append("Certifications present — signals commitment and credibility")
    if versions:
        strengths.append(f"Specific version experience: {', '.join(versions[:3])}")
    if matched:
        top = matched[:4]
        strengths.append(f"Core role skills present: {', '.join(top)}")
    return_strengths = strengths[:5] if strengths else ["Resume meets basic requirements"]

    # ── Red flags ─────────────────────────────────────────────────────────────
    red_flags = []
    if critical:
        red_flags.append(
            f"Missing job-title keywords ({', '.join(critical[:3])}) — "
            "recruiter may discard on first scan"
        )
    if not sections["summary"]:
        red_flags.append(
            "No professional summary — recruiters spend 6 sec on first pass; "
            "a tailored 3-line intro is the highest-ROI resume change"
        )
    if metrics < 3:
        red_flags.append(
            f"Only {metrics} quantified achievement{'s' if metrics != 1 else ''} detected — "
            "recruiters want impact numbers, not just duties"
        )
    if weak_v >= 2:
        red_flags.append(
            f"Passive language in {weak_v} place{'s' if weak_v != 1 else ''} "
            "('responsible for', 'helped') — replace with strong action verbs"
        )
    if not sections["skills"]:
        red_flags.append(
            "No dedicated Skills section detected — ATS scanners rely on this "
            "section for keyword extraction"
        )
    if required:
        red_flags.append(
            f"{len(required)} 'Required' skill{'s' if len(required) != 1 else ''} missing: "
            f"{', '.join(required[:3])}"
        )

    # ── Improvement plan (ranked) ─────────────────────────────────────────────
    improvements = []

    if critical:
        improvements.append({
            "priority": "HIGH",
            "section":  "Skills + Summary",
            "issue":    f"JD title keywords missing: {', '.join(critical)}",
            "action":   (
                "Add these VERBATIM to your Technical Skills section AND mention them in your "
                "Summary. These appear in the job title — the first strings both ATS and "
                "recruiters scan for."
            ),
            "keywords": critical,
        })

    if not sections["summary"]:
        role = jd_title or "this role"
        improvements.append({
            "priority": "HIGH",
            "section":  "Professional Summary",
            "issue":    "No summary/profile section found",
            "action":   (
                f"Add a 3-line summary at the top of your resume: (1) your title + years of exp, "
                f"(2) 2–3 core strengths aligned to {role}, (3) one differentiator. "
                "Example structure: '[Title] with X years in [domain]. Expertise in [A, B, C]. "
                "Delivered [impact statement].'"
            ),
            "keywords": [],
        })

    if required:
        improvements.append({
            "priority": "HIGH",
            "section":  "Technical Skills",
            "issue":    f"{len(required)} skill(s) marked 'Required' in JD are missing",
            "action":   (
                "Add these to Skills section using the exact JD wording. "
                "ATS matches strings literally — 'HCM Data Loader' ≠ 'HDL' to a parser."
            ),
            "keywords": required,
        })

    if metrics < 4:
        need = 4 - metrics
        improvements.append({
            "priority": "MEDIUM",
            "section":  "Experience Bullets",
            "issue":    f"Only {metrics} quantified result(s) — recruiters want impact, not duties",
            "action":   (
                f"Add numbers to at least {need + metrics} bullet points. "
                "Examples: '…reduced payroll processing by 30%', '…built 12 OIC integrations', "
                "'…supported 500+ end users'. Ask: How many? How much? How fast? What scale?"
            ),
            "keywords": [],
        })

    if weak_v >= 2:
        improvements.append({
            "priority": "MEDIUM",
            "section":  "Experience Bullets",
            "issue":    f"Passive language in {weak_v} place(s)",
            "action":   (
                "Start every bullet with a strong past-tense verb. "
                "Replace: 'Responsible for configuring…' → 'Configured…' | "
                "'Helped with migration' → 'Executed migration of…' | "
                "'Involved in design' → 'Designed and implemented…'"
            ),
            "keywords": [],
        })

    if preferred:
        improvements.append({
            "priority": "LOW",
            "section":  "Technical Skills / Experience",
            "issue":    f"{len(preferred)} preferred keyword(s) absent",
            "action":   (
                "Add these where you have even minor exposure — preferred skills differentiate "
                "candidates at the same ATS score. A single line in a project description counts."
            ),
            "keywords": preferred[:8],
        })

    if not sections["certifications"]:
        improvements.append({
            "priority": "LOW",
            "section":  "Certifications",
            "issue":    "No certifications listed",
            "action":   (
                "Add Oracle certifications (OCP, OCE) or any cloud/platform cert relevant to "
                "this role. Even 'In progress' certifications signal initiative to recruiters."
            ),
            "keywords": [],
        })

    return {
        "verdict":         verdict,
        "verdict_color":   vcolor,
        "interview_chance": interview,
        "recruiter_score": rec_score,
        "quality_score":   quality,
        "ats_score":       ats_score,
        "signals": {
            "strong_verbs": strong_v,
            "weak_language": weak_v,
            "metrics":       metrics,
            "max_years":     max_years,
            "sections":      sections,
            "versions":      versions,
        },
        "gap_breakdown": {
            "critical":  critical,
            "required":  required,
            "preferred": preferred,
        },
        "strengths":    return_strengths,
        "red_flags":    red_flags[:5],
        "improvements": improvements,
        "matched":      matched,
        "missing":      missing,
    }
