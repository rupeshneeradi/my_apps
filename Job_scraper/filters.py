"""
Job relevance and employment-type filters — v1.0.8

Two gates every job must pass:
  1. is_relevant()  — title/description contains a core keyword for its job type
  2. is_contract()  — strictly C2C / Corp-to-Corp / C2H / 1099 / Third-Party ONLY

Contract filter logic (4 steps, in order):
  STEP 1 — HARD EXCLUDE  : definitive W2/no-C2C language, or wrong domain → always FAIL
  STEP 2 — STRONG PASS   : explicit c2c / 1099 / corp-to-corp / third-party → PASS
  STEP 3 — SOFT EXCLUDE  : W2/full-time/salary signals with no C2C to save it → FAIL
  STEP 4 — TRUST PORTAL  : job came from a c2c-targeted search, no exclusion found → PASS
  else   — FAIL

v1.0.8 additions:
  • HARD_EXCLUDE: "cpq" / "configure price quote" — not in Oracle dev/ETL scope
  • SOFT_EXCLUDE: salary and FTE-benefit signals (annual salary, base salary, pto, etc.)
  • Cleaned up "Contract W2" / "W2 Contract" raw strings that had slipped in
"""
import re
import logging
from config import CONTRACT_STRONG, CORE_TITLE_TERMS

log = logging.getLogger(__name__)

# ── Title domain-signal words ─────────────────────────────────────────────────
# At least ONE of these must appear in the JOB TITLE for a job to pass
# relevance when the title itself doesn't directly match CORE_TITLE_TERMS.
# This prevents jobs like "Sr. Manager Full Stack Software Engineer" from
# passing solely because "Informatica" appears once as a preferred skill.
_DOMAIN_TITLE_WORDS: list[str] = [
    "oracle", "netsuite", "apex",
    "fusion", "hcm", "oic",
    "etl", "informatica",
    "pl/sql", "plsql",
    "ebs", "erp",
    "datastage", "talend", "odi",
    "data warehouse",
]

# ── Hard exclusions — always FAIL ─────────────────────────────────────────────
HARD_EXCLUDE: list[str] = [
    # Explicit "no c2c" language
    "no c2c", "not c2c", "no corp to corp", "no corp-to-corp",
    "not available for c2c", "c2c not available",
    "no third party", "no third-party", "no 3rd party",
    "no subcontract", "no subcontracting", "no sub-contract",
    "no contractors", "no independent contractor",
    "no vendor", "no vendors", "no agencies",
    # Explicit W2-only
    "w2 only", "w-2 only", "w2 candidates only", "w2 contractors only",
    "on w2 only", "must be on w2",
    # Explicit fulltime/permanent-only
    "full time only", "fulltime only", "full-time only",
    "permanent only", "direct hire only", "employees only",
    "not available for contract",
    # ── Wrong domain — out of scope for Oracle/ETL roles ──────────────────────
    "cpq",                    # Configure Price Quote (Oracle CPQ, Salesforce CPQ)
    "configure price quote",  # spelled out
]

# ── Soft exclusions — FAIL unless a STRONG C2C term is also present ────────────
SOFT_EXCLUDE: list[str] = [
    # Employment type signals
    "w2",              # bare "W2" without "only" — e.g. "W2 contract" → fail unless c2c saves it
    "full time",       # "full time position"
    "full-time",
    "fulltime",
    "permanent",       # "permanent role"
    "direct hire",     # "direct hire opportunity"
    "direct placement",
    "salaried",
    # FTE benefit signals — these almost never appear in genuine C2C postings
    "benefits package",
    "401k",
    "health insurance",
    # Salary / compensation signals — C2C postings say "rate" not "salary"
    "annual salary",
    "base salary",
    "salary range",
    "per annum",
    # Additional FTE perks
    "paid time off",
    "pto",
    "dental vision",
    "medical dental",
    "annual bonus",
    "signing bonus",
    "stock option",
    "equity compensation",
    "profit sharing",
]


def _text(job: dict) -> str:
    return (
        (job.get("title", "") or "") + " " +
        (job.get("description", "") or "")
    ).lower()


def _matches_any(text: str, terms: list[str]) -> bool:
    for term in terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text):
            return True
    return False


def is_relevant(job: dict) -> bool:
    """
    Relevance gate — two checks must both pass:

    1. TITLE SANITY: the job title must contain at least one direct CORE_TITLE_TERMS
       match OR one _DOMAIN_TITLE_WORDS signal.  Jobs whose titles are completely
       outside the Oracle/ETL domain (e.g. "Sr. Manager Full Stack Software Engineer",
       "Data Engineer (AWS/Spark)") are rejected here even if the description
       mentions a domain tool as a side/preferred skill.

    2. FULL TEXT: title+description must contain at least one CORE_TITLE_TERMS term
       for the assigned job_type.
    """
    job_type   = job.get("job_type", "")
    core_terms = CORE_TITLE_TERMS.get(job_type, [])
    if not core_terms:
        return True

    title = (job.get("title", "") or "").lower()
    text  = _text(job)

    # ── Check 1: title sanity ──────────────────────────────────────────────────
    title_has_core   = _matches_any(title, core_terms)
    title_has_domain = _matches_any(title, _DOMAIN_TITLE_WORDS)
    if not title_has_core and not title_has_domain:
        log.debug("TITLE-SANITY-FAIL: %s", job.get("title"))
        return False

    # ── Check 2: full text relevance ──────────────────────────────────────────
    if _matches_any(text, core_terms):
        return True

    log.debug("RELEVANCE-FAIL: %s | %s", job.get("title"), job_type)
    return False


def is_contract(job: dict) -> bool:
    """
    Strictly C2C / Corp-to-Corp / C2H / 1099 / Third-Party ONLY.
    W2, full-time, permanent, direct-hire, and salaried jobs are rejected.

    trust_portal (set by scraper) = job came from a c2c-targeted search;
    passes at Step 4 only if no exclusion language found.
    """
    text         = _text(job)
    trust_portal = job.get("c2c_search", False)

    # Step 1 — Hard exclude: definitive W2/no-C2C or wrong-domain language → always fail
    if _matches_any(text, HARD_EXCLUDE):
        log.debug("HARD-EXCLUDED: %s", job.get("title"))
        return False

    # Step 2 — Strong C2C term found → pass
    if _matches_any(text, CONTRACT_STRONG):
        return True

    # Step 3 — Soft exclude: FTE/W2/salary signal without any C2C to save it → fail
    if _matches_any(text, SOFT_EXCLUDE):
        log.debug("SOFT-EXCLUDED (no c2c term): %s", job.get("title"))
        return False

    # Step 4 — Portal was searched with c2c terms, no exclusion found → trust it
    if trust_portal:
        return True

    # No c2c signal at all
    log.debug("CONTRACT-FAIL (no signal): %s", job.get("title"))
    return False


def apply_filters(jobs: list[dict], skip_contract: bool = False) -> tuple[list[dict], dict]:
    """Apply relevance + strict C2C filters. Returns (passing_jobs, stats)."""
    total        = len(jobs)
    relevance_ok = [j for j in jobs if is_relevant(j)]
    contract_ok  = [j for j in relevance_ok if skip_contract or is_contract(j)]

    stats = {
        "total_raw":         total,
        "after_relevance":   len(relevance_ok),
        "after_contract":    len(contract_ok),
        "dropped_relevance": total - len(relevance_ok),
        "dropped_contract":  len(relevance_ok) - len(contract_ok),
    }
    log.info(
        "Filter results: %d raw → %d relevant → %d C2C/1099/corp-to-corp",
        total, len(relevance_ok), len(contract_ok),
    )
    return contract_ok, stats
