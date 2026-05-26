"""
Job Application Tracker
────────────────────────────────────────────────────────────────────────────
SQLite-backed, zero extra dependencies beyond stdlib.
Stores every job application with status, notes, and ATS score.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "tracker.db"

STATUSES = ["applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]
STATUS_LABEL = {
    "applied":      "Applied",
    "phone_screen": "Phone Screen",
    "interview":    "Interview",
    "offer":        "Offer",
    "rejected":     "Rejected",
    "withdrawn":    "Withdrawn",
}


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        # ── Application Tracker ──────────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                company        TEXT    DEFAULT '',
                role           TEXT    DEFAULT '',
                jd_url         TEXT    DEFAULT '',
                jd_text        TEXT    DEFAULT '',
                date_applied   TEXT    DEFAULT '',
                status         TEXT    DEFAULT 'applied',
                ats_score      INTEGER DEFAULT NULL,
                resume_version TEXT    DEFAULT '',
                salary_range   TEXT    DEFAULT '',
                source         TEXT    DEFAULT '',
                notes          TEXT    DEFAULT '',
                created_at     TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                updated_at     TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
            )
        """)
        # Migrate older DBs
        for col, defn in [("jd_text","TEXT DEFAULT ''"),
                          ("resume_version","TEXT DEFAULT ''")]:
            try:
                c.execute(f"ALTER TABLE applications ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── Scraped Jobs (pipeline data) ─────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS scraped_jobs (
                id           TEXT    PRIMARY KEY,
                pipeline     TEXT    NOT NULL DEFAULT 'opt',
                title        TEXT    DEFAULT '',
                company      TEXT    DEFAULT '',
                location     TEXT    DEFAULT '',
                url          TEXT    DEFAULT '',
                portal       TEXT    DEFAULT '',
                job_type     TEXT    DEFAULT '',
                jd_text      TEXT    DEFAULT '',
                jd_keywords  TEXT    DEFAULT '[]',
                ats_score    INTEGER DEFAULT 0,
                resume_used  TEXT    DEFAULT '',
                matched_kws  TEXT    DEFAULT '[]',
                gap_kws      TEXT    DEFAULT '[]',
                gap_critical TEXT    DEFAULT '[]',
                gap_required TEXT    DEFAULT '[]',
                gap_preferred TEXT   DEFAULT '[]',
                opt_friendly INTEGER DEFAULT 0,
                opt_score    INTEGER DEFAULT 0,
                is_remote    INTEGER DEFAULT 0,
                emp_type     TEXT    DEFAULT '',
                salary_range TEXT    DEFAULT '',
                posted_date  TEXT    DEFAULT '',
                scraped_date TEXT    DEFAULT '',
                scored_at    TEXT    DEFAULT '',
                status        TEXT    DEFAULT 'new',
                resume_domain TEXT    DEFAULT '',
                jd_domain     TEXT    DEFAULT '',
                role_fit_score INTEGER DEFAULT 0,
                combined_score INTEGER DEFAULT 0
            )
        """)

        # Migrate older scraped_jobs rows (add new columns if missing)
        for col, defn in [
            ("resume_domain",  "TEXT    DEFAULT ''"),
            ("jd_domain",      "TEXT    DEFAULT ''"),
            ("role_fit_score", "INTEGER DEFAULT 0"),
            ("combined_score", "INTEGER DEFAULT 0"),
        ]:
            try:
                c.execute(f"ALTER TABLE scraped_jobs ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── Score History (every ATS scoring session) ────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_name     TEXT    DEFAULT '',
                jd_title        TEXT    DEFAULT '',
                jd_text         TEXT    DEFAULT '',
                ats_score       INTEGER DEFAULT 0,
                recruiter_score INTEGER DEFAULT 0,
                quality_score   INTEGER DEFAULT 0,
                interview_chance TEXT   DEFAULT '',
                verdict         TEXT    DEFAULT '',
                matched_kws     TEXT    DEFAULT '[]',
                gap_kws         TEXT    DEFAULT '[]',
                gap_critical    TEXT    DEFAULT '[]',
                gap_required    TEXT    DEFAULT '[]',
                gap_preferred   TEXT    DEFAULT '[]',
                scraped_job_id  TEXT    DEFAULT NULL,
                scored_at       TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
            )
        """)

        # ── Keyword Log (recurring gaps & trends) ────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS keyword_log (
                keyword        TEXT NOT NULL,
                role_context   TEXT NOT NULL DEFAULT '',
                times_seen     INTEGER DEFAULT 0,
                times_as_gap   INTEGER DEFAULT 0,
                times_filled   INTEGER DEFAULT 0,
                last_seen_date TEXT    DEFAULT '',
                PRIMARY KEY (keyword, role_context)
            )
        """)


def _row(id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM applications WHERE id=?", (id,)).fetchone()
        return dict(r) if r else None


def add_application(d: dict) -> dict:
    init_db()
    new_id = None
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO applications
               (company,role,jd_url,date_applied,status,ats_score,salary_range,source,notes,resume_version)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                (d.get("company") or "").strip(),
                (d.get("role")    or "").strip(),
                (d.get("jd_url")  or "").strip(),
                (d.get("date_applied") or datetime.now().strftime("%Y-%m-%d")),
                d.get("status", "applied"),
                d.get("ats_score") or None,
                (d.get("salary_range")   or "").strip(),
                (d.get("source")         or "").strip(),
                (d.get("notes")          or "").strip(),
                (d.get("resume_version") or "").strip(),
            ),
        )
        new_id = cur.lastrowid
    return _row(new_id)


def list_applications(status: str | None = None) -> list[dict]:
    init_db()
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM applications WHERE status=? ORDER BY date_applied DESC, id DESC",
                (status,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM applications ORDER BY date_applied DESC, id DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def update_application(id: int, d: dict) -> dict | None:
    init_db()
    allowed = {"company", "role", "jd_url", "date_applied", "status",
               "ats_score", "salary_range", "source", "notes", "resume_version"}
    updates = {k: v for k, v in d.items() if k in allowed}
    if not updates:
        return _row(id)
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cols = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [id]
    with _conn() as c:
        c.execute(f"UPDATE applications SET {cols} WHERE id=?", vals)
    return _row(id)


def delete_application(id: int) -> bool:
    init_db()
    with _conn() as c:
        c.execute("DELETE FROM applications WHERE id=?", (id,))
    return True


def get_stats() -> dict:
    apps = list_applications()
    total = len(apps)
    by_status: dict[str, int] = {}
    for a in apps:
        s = a["status"]
        by_status[s] = by_status.get(s, 0) + 1

    responded = sum(by_status.get(s, 0) for s in ["phone_screen", "interview", "offer"])
    response_rate = round(responded / total * 100) if total else 0
    offer_rate    = round(by_status.get("offer", 0) / total * 100) if total else 0
    scored = [a["ats_score"] for a in apps if a["ats_score"] is not None]
    avg_ats = round(sum(scored) / len(scored)) if scored else None

    return {
        "total":         total,
        "by_status":     by_status,
        "response_rate": response_rate,
        "offer_rate":    offer_rate,
        "avg_ats":       avg_ats,
        "active":        total - by_status.get("rejected", 0) - by_status.get("withdrawn", 0),
    }
