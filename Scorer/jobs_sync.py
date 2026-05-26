"""
Pipeline Sync — connects scraped job databases to the ATS scorer.

Pipelines supported:
  • opt   — reads opt_jobscraper/jobs.db  (OPT-friendly DevOps/Cloud jobs)
  • portal — reads Job_scraper Google Sheets data (Oracle/ETL portal jobs)

For each job with a JD, scores it against the user's loaded resumes,
keeps only the best-scoring resume per job, stores everything in
Scorer/tracker.db → scraped_jobs table, and logs keyword gaps to keyword_log.

Threshold: ats_score >= 40 to be stored (configurable).
"""
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent
OPT_DB      = BASE_DIR.parent / "opt_jobscraper" / "jobs.db"
OPT_OUTPUT  = BASE_DIR.parent / "opt_jobscraper" / "output"
JOB_SCRAPER = BASE_DIR.parent / "Job_scraper"

sys.path.insert(0, str(JOB_SCRAPER))
sys.path.insert(0, str(BASE_DIR))

from role_classifier import classify, role_fit, combined_score, domain_label, is_non_it

ATS_THRESHOLD = 40   # minimum ATS score to store a job

import csv as _csv


# ── Lazy imports (don't fail at module load if deps missing) ──────────────────

def _ats_scorer():
    from ats_scorer import score_resume
    return score_resume


def _tracker_conn():
    from tracker import DB_PATH, init_db
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── Keyword gap logging ───────────────────────────────────────────────────────

def _log_keywords(conn: sqlite3.Connection,
                  matched: list[str], missing: list[str],
                  role_context: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    for kw in matched:
        conn.execute("""
            INSERT INTO keyword_log (keyword, role_context, times_seen, times_filled, last_seen_date)
            VALUES (?, ?, 1, 1, ?)
            ON CONFLICT(keyword, role_context) DO UPDATE SET
                times_seen   = times_seen   + 1,
                times_filled = times_filled + 1,
                last_seen_date = ?
        """, (kw.lower(), role_context, today, today))
    for kw in missing:
        conn.execute("""
            INSERT INTO keyword_log (keyword, role_context, times_seen, times_as_gap, last_seen_date)
            VALUES (?, ?, 1, 1, ?)
            ON CONFLICT(keyword, role_context) DO UPDATE SET
                times_seen  = times_seen  + 1,
                times_as_gap = times_as_gap + 1,
                last_seen_date = ?
        """, (kw.lower(), role_context, today, today))
    conn.commit()


# ── Gap priority breakdown (mirrors analyzer.py logic) ────────────────────────

def _gap_breakdown(jd_text: str, jd_title: str, missing: list[str]) -> dict:
    import re
    title_l = jd_title.lower()
    _PREF   = re.compile(r'\b(preferred|nice to have|plus|bonus|desired|good to have)\b', re.I)
    _REQ    = re.compile(r'\b(required|must have|mandatory|minimum)\b', re.I)
    req_lines, pref_lines, mode = [], [], "required"
    for line in jd_text.split("\n"):
        if _PREF.search(line):   mode = "preferred"
        elif _REQ.search(line):  mode = "required"
        (req_lines if mode == "required" else pref_lines).append(line.lower())
    req_text  = " ".join(req_lines)
    pref_text = " ".join(pref_lines)

    def _in(kw, text): return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))

    critical  = [k for k in missing if _in(k, title_l)]
    required  = [k for k in missing if k not in critical and _in(k, req_text)]
    preferred = [k for k in missing if k not in critical and k not in required]
    return {"critical": critical, "required": required, "preferred": preferred}


# ── OPT pipeline sync ─────────────────────────────────────────────────────────

def _load_opt_csv_jobs() -> dict[str, dict]:
    """
    Load all CSV exports from opt_jobscraper/output/ and return a dict
    keyed by job id with description populated.
    Merges multiple CSVs — latest file wins on conflict.
    """
    if not OPT_OUTPUT.exists():
        return {}
    csvs = sorted(OPT_OUTPUT.glob("jobs_*.csv"))
    merged: dict[str, dict] = {}
    for csv_path in csvs:
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    jid = row.get("id", "").strip()
                    if not jid:
                        continue
                    existing = merged.get(jid)
                    new_desc = (row.get("description") or "").strip()
                    # keep entry with longer/newer description
                    if existing is None or len(new_desc) > len(existing.get("description") or ""):
                        merged[jid] = row
        except Exception as e:
            log.warning("Could not read CSV %s: %s", csv_path, e)
    log.info("OPT CSVs: %d unique jobs with descriptions loaded", len(merged))
    return merged


def _backfill_opt_db_descriptions(csv_jobs: dict[str, dict]) -> int:
    """Update description/is_remote/emp_type in opt DB from CSV data."""
    if not OPT_DB.exists() or not csv_jobs:
        return 0
    conn = sqlite3.connect(str(OPT_DB))
    updated = 0
    try:
        for jid, job in csv_jobs.items():
            desc = (job.get("description") or "").strip()
            if len(desc) < 80:
                continue
            is_remote = job.get("is_remote") or 0
            if isinstance(is_remote, str):
                is_remote = 1 if is_remote.lower() in ("1","true","yes") else 0
            conn.execute(
                "UPDATE jobs SET description=?, is_remote=?, emp_type=? WHERE id=? AND (description IS NULL OR description='')",
                (desc, int(is_remote), job.get("emp_type",""), jid)
            )
            updated += 1
        conn.commit()
    finally:
        conn.close()
    log.info("OPT DB backfill: updated %d rows with description", updated)
    return updated


def sync_opt_pipeline(resumes: dict[str, str],
                      threshold: int = ATS_THRESHOLD) -> dict:
    """
    Score opt_jobscraper jobs against resumes, store in scraped_jobs (pipeline='opt').
    Sources: opt DB + CSV exports (CSVs contain description text the DB may lack).
    """
    if not OPT_DB.exists() and not OPT_OUTPUT.exists():
        return {"pipeline": "opt", "read": 0, "stored": 0, "skipped": 0,
                "error": "OPT DB and output directory not found"}

    score_resume = _ats_scorer()

    # ── Load CSV jobs (have description) and backfill DB ─────────────────────
    csv_jobs = _load_opt_csv_jobs()
    if csv_jobs:
        _backfill_opt_db_descriptions(csv_jobs)

    # ── Read from DB (now backfilled) ─────────────────────────────────────────
    jobs: list[dict] = []
    if OPT_DB.exists():
        opt_conn = sqlite3.connect(str(OPT_DB))
        opt_conn.row_factory = sqlite3.Row
        try:
            for stmt in [
                "ALTER TABLE jobs ADD COLUMN description TEXT",
                "ALTER TABLE jobs ADD COLUMN is_remote INTEGER DEFAULT 0",
                "ALTER TABLE jobs ADD COLUMN emp_type TEXT DEFAULT ''",
            ]:
                try:
                    opt_conn.execute(stmt); opt_conn.commit()
                except sqlite3.OperationalError:
                    pass
            rows = opt_conn.execute("""
                SELECT id, title, company, location, url, portal, job_type,
                       score AS opt_score, opt_friendly, posted_date, scraped_date,
                       COALESCE(description,'') AS description,
                       COALESCE(is_remote,0)    AS is_remote,
                       COALESCE(emp_type,'')    AS emp_type
                FROM jobs ORDER BY scraped_date DESC
            """).fetchall()
            jobs = [dict(r) for r in rows]
        finally:
            opt_conn.close()

    # ── Merge in CSV jobs that may not be in DB yet ───────────────────────────
    db_ids = {j["id"] for j in jobs}
    db_map = {j["id"]: j for j in jobs}

    # Patch descriptions from CSV where DB still has empty
    for jid, csv_job in csv_jobs.items():
        desc = (csv_job.get("description") or "").strip()
        if jid in db_map:
            if not db_map[jid].get("description"):
                db_map[jid]["description"] = desc
        else:
            # Job in CSV but not DB — add it
            db_map[jid] = {
                "id":          jid,
                "title":       csv_job.get("title",""),
                "company":     csv_job.get("company",""),
                "location":    csv_job.get("location",""),
                "url":         csv_job.get("url",""),
                "portal":      csv_job.get("portal",""),
                "job_type":    csv_job.get("job_type",""),
                "opt_score":   int(csv_job.get("score") or 0),
                "opt_friendly":int(csv_job.get("opt_friendly") or 0),
                "is_remote":   int(csv_job.get("is_remote") or 0),
                "emp_type":    csv_job.get("emp_type",""),
                "posted_date": csv_job.get("posted_date",""),
                "scraped_date":csv_job.get("scraped_date",""),
                "description": desc,
            }
    jobs = list(db_map.values())
    log.info("OPT sync: %d total jobs (DB + CSV merge)", len(jobs))

    stored = skipped = no_jd = 0
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Wipe stale OPT rows so every sync is fully role-aware (clean slate)
    _wipe = _tracker_conn()
    _wipe.execute("DELETE FROM scraped_jobs WHERE pipeline='opt'")
    _wipe.commit()
    _wipe.close()

    tracker = _tracker_conn()
    try:
        for job in jobs:
            jd_text = (job.get("description") or "").strip()
            if len(jd_text) < 80:
                no_jd += 1
                continue

            title    = job.get("title", "")
            emp_type = job.get("job_type") or job.get("emp_type") or "Full-time"

            # ── Classify JD domain ────────────────────────────────────────────
            jd_domain, jd_conf, _ = classify(jd_text + " " + title)

            # Skip non-IT jobs entirely (manufacturing, automotive, biomedical, etc.)
            # These slip through the scraper occasionally and always false-score
            # because common English words ("functions", "operations", "controls")
            # collide with Oracle/DevOps keyword banks.
            if is_non_it(jd_domain):
                skipped += 1
                log.debug(
                    "SKIP non_it domain | %s | %s", title,
                    "classified as non-IT industry role"
                )
                continue

            # ── Score against all resumes — pick best COMBINED score ──────────
            best_combined = -1
            best_ats = 0
            best_resume = ""
            best_matched: list[str] = []
            best_missing: list[str] = []
            best_fit = 0
            best_resume_domain = ""

            for rname, rtext in resumes.items():
                # Pass jd_domain so scorer uses only that domain's keyword bank
                # (prevents Oracle "benefits/packages/functions" contaminating DevOps scores)
                ats, matched, missing = score_resume(
                    rtext, jd_text, jd_title=title, domain=jd_domain
                )
                res_domain, _, _ = classify(rtext)
                fit     = role_fit(res_domain, jd_domain)
                comb    = combined_score(ats, fit)

                if comb > best_combined:
                    best_combined      = comb
                    best_ats           = ats
                    best_resume        = rname
                    best_matched       = matched
                    best_missing       = missing
                    best_fit           = fit
                    best_resume_domain = res_domain

            # ── Apply combined threshold ──────────────────────────────────────
            if best_combined < threshold:
                skipped += 1
                continue

            gaps    = _gap_breakdown(jd_text, title, best_missing)
            all_kws = sorted(set(best_matched + best_missing))

            tracker.execute("""
                INSERT INTO scraped_jobs
                    (id, pipeline, title, company, location, url, portal, job_type,
                     jd_text, jd_keywords, ats_score, resume_used,
                     matched_kws, gap_kws, gap_critical, gap_required, gap_preferred,
                     opt_friendly, opt_score, is_remote, emp_type,
                     posted_date, scraped_date, scored_at, status,
                     resume_domain, jd_domain, role_fit_score, combined_score)
                VALUES
                    (?, 'opt', ?, ?, ?, ?, ?, ?,
                     ?, ?, ?, ?,
                     ?, ?, ?, ?, ?,
                     ?, ?, ?, ?,
                     ?, ?, ?, 'new',
                     ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    ats_score      = excluded.ats_score,
                    resume_used    = excluded.resume_used,
                    matched_kws    = excluded.matched_kws,
                    gap_kws        = excluded.gap_kws,
                    gap_critical   = excluded.gap_critical,
                    gap_required   = excluded.gap_required,
                    gap_preferred  = excluded.gap_preferred,
                    jd_keywords    = excluded.jd_keywords,
                    resume_domain  = excluded.resume_domain,
                    jd_domain      = excluded.jd_domain,
                    role_fit_score = excluded.role_fit_score,
                    combined_score = excluded.combined_score,
                    scored_at      = excluded.scored_at
            """, (
                job["id"], title,
                job.get("company",""), job.get("location",""),
                job.get("url",""), job.get("portal",""), emp_type,
                jd_text,
                json.dumps(all_kws), int(best_ats), best_resume,
                json.dumps(best_matched), json.dumps(best_missing),
                json.dumps(gaps["critical"]), json.dumps(gaps["required"]),
                json.dumps(gaps["preferred"]),
                int(job.get("opt_friendly") or 0), int(job.get("opt_score") or 0),
                int(job.get("is_remote") or 0), emp_type,
                job.get("posted_date",""), job.get("scraped_date",""), now,
                best_resume_domain, jd_domain, best_fit, best_combined,
            ))
            tracker.commit()

            _log_keywords(tracker, best_matched, best_missing,
                          role_context=jd_domain)
            stored += 1

    finally:
        tracker.close()

    log.info("OPT sync done — stored: %d, skipped (below threshold): %d, no JD: %d",
             stored, skipped, no_jd)
    return {
        "pipeline": "opt",
        "read":     len(jobs),
        "stored":   stored,
        "skipped":  skipped,
        "no_jd":    no_jd,
        "threshold": threshold,
    }


# ── Portal pipeline sync (Google Sheets → scraped_jobs) ──────────────────────

def sync_portal_pipeline(resumes: dict[str, str],
                         threshold: int = ATS_THRESHOLD) -> dict:
    """
    Read Job_scraper Google Sheets data via drive_resumes-style loader.
    Falls back gracefully if Google Sheets is unavailable.
    """
    try:
        sys.path.insert(0, str(JOB_SCRAPER))
        from tracker import get_all_jobs  # type: ignore
        portal_jobs = get_all_jobs()
    except Exception as exc:
        log.warning("Portal sync: could not load jobs from Google Sheets — %s", exc)
        return {"pipeline": "portal", "read": 0, "stored": 0, "skipped": 0,
                "error": str(exc)}

    if not portal_jobs:
        return {"pipeline": "portal", "read": 0, "stored": 0, "skipped": 0}

    score_resume = _ats_scorer()
    stored = skipped = no_jd = 0
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    tracker = _tracker_conn()
    try:
        for job in portal_jobs:
            jd_text = (job.get("description") or job.get("jd_text") or "").strip()
            if len(jd_text) < 80:
                no_jd += 1
                continue

            job_id = str(job.get("id") or job.get("url") or "")
            if not job_id:
                continue
            # prefix to avoid collision with opt IDs
            job_id = f"portal-{job_id}"
            title = job.get("title") or job.get("role") or ""

            # Classify domain and skip non-IT jobs
            jd_domain, _, _ = classify(jd_text + " " + title)
            if is_non_it(jd_domain):
                skipped += 1
                log.debug("SKIP non_it domain (portal) | %s", title)
                continue

            best_score, best_resume, best_matched, best_missing = 0, "", [], []
            for rname, rtext in resumes.items():
                ats, matched, missing = score_resume(
                    rtext, jd_text, jd_title=title, domain=jd_domain
                )
                if ats > best_score:
                    best_score, best_resume = ats, rname
                    best_matched, best_missing = matched, missing

            if best_score < threshold:
                skipped += 1
                continue

            gaps = _gap_breakdown(jd_text, title, best_missing)
            all_kws = sorted(set(best_matched + best_missing))

            tracker.execute("""
                INSERT INTO scraped_jobs
                    (id, pipeline, title, company, location, url, portal, job_type,
                     jd_text, jd_keywords, ats_score, resume_used,
                     matched_kws, gap_kws, gap_critical, gap_required, gap_preferred,
                     opt_friendly, opt_score, is_remote, emp_type,
                     posted_date, scraped_date, scored_at, status)
                VALUES
                    (?, 'portal', ?, ?, ?, ?, ?, ?,
                     ?, ?, ?, ?,
                     ?, ?, ?, ?, ?,
                     0, 0, ?, ?,
                     ?, ?, ?, 'new')
                ON CONFLICT(id) DO UPDATE SET
                    ats_score    = excluded.ats_score,
                    resume_used  = excluded.resume_used,
                    matched_kws  = excluded.matched_kws,
                    gap_kws      = excluded.gap_kws,
                    gap_critical = excluded.gap_critical,
                    gap_required = excluded.gap_required,
                    gap_preferred= excluded.gap_preferred,
                    jd_keywords  = excluded.jd_keywords,
                    scored_at    = excluded.scored_at
            """, (
                job_id, title,
                job.get("company", ""), job.get("location", ""),
                job.get("url", ""), job.get("portal", ""), job.get("job_type", ""),
                jd_text,
                json.dumps(all_kws), int(best_score), best_resume,
                json.dumps(best_matched), json.dumps(best_missing),
                json.dumps(gaps["critical"]), json.dumps(gaps["required"]),
                json.dumps(gaps["preferred"]),
                int(job.get("is_remote") or 0), job.get("emp_type", ""),
                job.get("posted_date", ""), job.get("scraped_date", now[:10]), now,
            ))
            tracker.commit()

            _log_keywords(tracker, best_matched, best_missing,
                          role_context=title.split()[0].lower() if title else "portal")
            stored += 1

    finally:
        tracker.close()

    return {
        "pipeline": "portal",
        "read":     len(portal_jobs),
        "stored":   stored,
        "skipped":  skipped,
        "no_jd":    no_jd,
        "threshold": threshold,
    }


# ── List & update helpers (called by app.py routes) ──────────────────────────

def list_pipeline_jobs(pipeline: str | None = None,
                       min_ats: int = 0,
                       status: str | None = None) -> list[dict]:
    conn = _tracker_conn()
    try:
        clauses, params = ["1=1"], []
        if pipeline:
            clauses.append("pipeline = ?"); params.append(pipeline)
        if min_ats:
            clauses.append("ats_score >= ?"); params.append(min_ats)
        if status:
            clauses.append("status = ?"); params.append(status)
        sql = ("SELECT id, pipeline, title, company, location, url, portal, job_type,"
               " jd_keywords, ats_score, resume_used, matched_kws, gap_kws,"
               " gap_critical, gap_required, gap_preferred,"
               " opt_friendly, opt_score, is_remote, emp_type,"
               " salary_range, posted_date, scraped_date, scored_at, status,"
               " COALESCE(resume_domain,'') AS resume_domain,"
               " COALESCE(jd_domain,'')     AS jd_domain,"
               " COALESCE(role_fit_score,0) AS role_fit_score,"
               " COALESCE(combined_score,0) AS combined_score"
               " FROM scraped_jobs"
               f" WHERE {' AND '.join(clauses)}"
               " ORDER BY combined_score DESC, ats_score DESC, scored_at DESC")
        rows = conn.execute(sql, params).fetchall()
        jobs = []
        for r in rows:
            d = dict(r)
            for field in ("jd_keywords", "matched_kws", "gap_kws",
                          "gap_critical", "gap_required", "gap_preferred"):
                try:
                    d[field] = json.loads(d.get(field) or "[]")
                except Exception:
                    d[field] = []
            jobs.append(d)
        return jobs
    finally:
        conn.close()


def get_pipeline_job(job_id: str) -> dict | None:
    """Return single job including full jd_text."""
    conn = _tracker_conn()
    try:
        r = conn.execute("SELECT * FROM scraped_jobs WHERE id=?", (job_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        for field in ("jd_keywords", "matched_kws", "gap_kws",
                      "gap_critical", "gap_required", "gap_preferred"):
            try:
                d[field] = json.loads(d.get(field) or "[]")
            except Exception:
                d[field] = []
        return d
    finally:
        conn.close()


def update_pipeline_status(job_id: str, status: str) -> bool:
    conn = _tracker_conn()
    try:
        conn.execute("UPDATE scraped_jobs SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        return True
    finally:
        conn.close()


def pipeline_stats() -> dict:
    conn = _tracker_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM scraped_jobs").fetchone()[0]
        opt   = conn.execute("SELECT COUNT(*) FROM scraped_jobs WHERE pipeline='opt'").fetchone()[0]
        portal= conn.execute("SELECT COUNT(*) FROM scraped_jobs WHERE pipeline='portal'").fetchone()[0]
        new_c = conn.execute("SELECT COUNT(*) FROM scraped_jobs WHERE status='new'").fetchone()[0]
        saved = conn.execute("SELECT COUNT(*) FROM scraped_jobs WHERE status='saved'").fetchone()[0]
        applied=conn.execute("SELECT COUNT(*) FROM scraped_jobs WHERE status='applied'").fetchone()[0]
        avg_r = conn.execute("SELECT AVG(ats_score) FROM scraped_jobs WHERE ats_score > 0").fetchone()[0]
        top_r = conn.execute(
            "SELECT id, title, company, ats_score FROM scraped_jobs ORDER BY ats_score DESC LIMIT 5"
        ).fetchall()
        return {
            "total": total, "opt": opt, "portal": portal,
            "new": new_c, "saved": saved, "applied": applied,
            "avg_ats": round(avg_r) if avg_r else 0,
            "top_jobs": [dict(zip(["id","title","company","ats_score"], r)) for r in top_r],
        }
    finally:
        conn.close()


# ── Score history helpers ─────────────────────────────────────────────────────

def log_score_session(data: dict) -> None:
    """Persist one scoring session to score_history + keyword_log."""
    conn = _tracker_conn()
    try:
        conn.execute("""
            INSERT INTO score_history
                (resume_name, jd_title, jd_text, ats_score, recruiter_score,
                 quality_score, interview_chance, verdict,
                 matched_kws, gap_kws, gap_critical, gap_required, gap_preferred,
                 scraped_job_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("resume_name", ""),
            data.get("jd_title", ""),
            data.get("jd_text", ""),
            int(data.get("ats_score", 0)),
            int(data.get("recruiter_score", 0)),
            int(data.get("quality_score", 0)),
            data.get("interview_chance", ""),
            data.get("verdict", ""),
            json.dumps(data.get("matched_kws", [])),
            json.dumps(data.get("gap_kws", [])),
            json.dumps(data.get("gap_critical", [])),
            json.dumps(data.get("gap_required", [])),
            json.dumps(data.get("gap_preferred", [])),
            data.get("scraped_job_id"),
        ))
        conn.commit()

        # Also update keyword_log
        role = data.get("jd_title", "").split()[0].lower() if data.get("jd_title") else "manual"
        _log_keywords(conn,
                      data.get("matched_kws", []),
                      data.get("gap_kws", []),
                      role_context=role)
    finally:
        conn.close()


def list_score_history(limit: int = 50) -> list[dict]:
    conn = _tracker_conn()
    try:
        rows = conn.execute("""
            SELECT id, resume_name, jd_title, ats_score, recruiter_score,
                   quality_score, interview_chance, verdict,
                   matched_kws, gap_kws, gap_critical, gap_required, gap_preferred,
                   scraped_job_id, scored_at
            FROM score_history
            ORDER BY scored_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for f in ("matched_kws","gap_kws","gap_critical","gap_required","gap_preferred"):
                try:    d[f] = json.loads(d.get(f) or "[]")
                except: d[f] = []
            result.append(d)
        return result
    finally:
        conn.close()


def top_keyword_gaps(limit: int = 30) -> list[dict]:
    conn = _tracker_conn()
    try:
        rows = conn.execute("""
            SELECT keyword, role_context, times_seen, times_as_gap,
                   times_filled, last_seen_date
            FROM keyword_log
            WHERE times_as_gap > 0
            ORDER BY times_as_gap DESC, times_seen DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(zip(
            ["keyword","role_context","times_seen","times_as_gap","times_filled","last_seen_date"],
            r
        )) for r in rows]
    finally:
        conn.close()
