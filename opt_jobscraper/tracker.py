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
    score        INTEGER,
    opt_friendly INTEGER,
    posted_date  TEXT,
    scraped_date TEXT,
    notified     INTEGER DEFAULT 0
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute(DDL)
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
            INSERT OR IGNORE INTO jobs
            (id, title, company, location, url, portal, job_type,
             score, opt_friendly, posted_date, scraped_date)
            VALUES
            (:id, :title, :company, :location, :url, :portal, :job_type,
             :score, :opt_friendly, :posted_date, :scraped_date)
            """,
            jobs,
        )
        c.commit()
    log.info("Tracker: saved %d jobs", len(jobs))


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
                   score, opt_friendly, posted_date, scraped_date
            FROM jobs
            WHERE notified=0 AND score >= ?
            ORDER BY score DESC
            """,
            (min_score,),
        ).fetchall()
    cols = ["id","title","company","location","url","portal","job_type",
            "score","opt_friendly","posted_date","scraped_date"]
    return [dict(zip(cols, r)) for r in rows]
