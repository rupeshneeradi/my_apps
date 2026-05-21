"""SQLite-backed job tracker — dedup across pipeline runs."""
import logging
import sqlite3

from config import DB_PATH

log = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    title        TEXT,
    company      TEXT,
    location     TEXT,
    url          TEXT,
    portal       TEXT,
    job_type     TEXT,
    score        INTEGER DEFAULT 0,
    opt_friendly INTEGER,
    posted_date  TEXT,
    scraped_date TEXT,
    notified     INTEGER DEFAULT 0,
    description  TEXT,
    is_remote    INTEGER DEFAULT 0
);
"""

DDL_MIGRATE = [
    "ALTER TABLE jobs ADD COLUMN description TEXT",
    "ALTER TABLE jobs ADD COLUMN is_remote INTEGER DEFAULT 0",
]


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute(DDL)
    # migrate older DBs that don't have description / is_remote columns
    for stmt in DDL_MIGRATE:
        try:
            c.execute(stmt)
        except sqlite3.OperationalError:
            pass  # column already exists
    c.commit()
    return c


def filter_new(jobs: list[dict]) -> list[dict]:
    if not jobs:
        return []
    with _conn() as c:
        existing = {row[0] for row in c.execute("SELECT id FROM jobs").fetchall()}
    new = [j for j in jobs if j["id"] not in existing]
    log.info("Tracker: %d new / %d total (skipped %d seen)",
             len(new), len(jobs), len(jobs) - len(new))
    return new


def save(jobs: list[dict]) -> None:
    if not jobs:
        return
    with _conn() as c:
        c.executemany(
            """
            INSERT INTO jobs
                (id, title, company, location, url, portal, job_type,
                 score, opt_friendly, posted_date, scraped_date, description, is_remote)
            VALUES
                (:id, :title, :company, :location, :url, :portal, :job_type,
                 :score, :opt_friendly, :posted_date, :scraped_date, :description, :is_remote)
            ON CONFLICT(id) DO UPDATE SET
                score        = excluded.score,
                opt_friendly = excluded.opt_friendly,
                description  = excluded.description,
                is_remote    = excluded.is_remote
            WHERE excluded.score > jobs.score   -- only overwrite if new score is better
            """,
            [{**j, "description": j.get("description", ""), "is_remote": int(j.get("is_remote", False))} for j in jobs],
        )
        c.commit()
    log.info("Tracker: saved/updated %d jobs", len(jobs))


def mark_notified(job_ids: list[str]) -> None:
    if not job_ids:
        return
    with _conn() as c:
        c.executemany(
            "UPDATE jobs SET notified=1 WHERE id=?",
            [(jid,) for jid in job_ids],
        )
        c.commit()


def unnotified(min_score: int = 0) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT id, title, company, location, url, portal, job_type,
                   score, opt_friendly, posted_date, scraped_date,
                   description, is_remote
            FROM jobs
            WHERE notified=0 AND score >= ?
            ORDER BY score DESC
            """,
            (min_score,),
        ).fetchall()
    cols = ["id","title","company","location","url","portal","job_type",
            "score","opt_friendly","posted_date","scraped_date",
            "description","is_remote"]
    return [dict(zip(cols, r)) for r in rows]


def rescore_all(score_fn) -> int:
    """Re-score every job in DB that has score=0 using score_fn(job dict)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, company, description, is_remote, job_type, posted_date "
            "FROM jobs WHERE score = 0"
        ).fetchall()
        cols = ["id","title","company","description","is_remote","job_type","posted_date"]
        jobs = [dict(zip(cols, r)) for r in rows]

        updated = 0
        for job in jobs:
            new_score = score_fn(job)
            if new_score > 0:
                c.execute("UPDATE jobs SET score=? WHERE id=?", (new_score, job["id"]))
                updated += 1
        c.commit()
    return updated
