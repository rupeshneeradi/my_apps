"""
Main pipeline orchestrator.
Flow: scrape → filter → dedup → score → save → notify → export CSV
"""
import csv
import logging
import os
import sys
from datetime import datetime

from config import OUTPUT_DIR, SCORE_MIN_NOTIFY

import scraper
import filters
import tracker
import scorer
import notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def export_csv(jobs: list[dict], path: str) -> None:
    if not jobs:
        return
    fields = ["id", "title", "company", "location", "url", "portal", "job_type",
              "score", "opt_friendly", "is_remote", "emp_type",
              "posted_date", "scraped_date", "description"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)
    log.info("Exported %d jobs → %s", len(jobs), path)


def run(notify: bool = True) -> list[dict]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log.info("=" * 60)
    log.info("OPT DevOps Job Scraper  |  run %s", stamp)
    log.info("=" * 60)

    # 1. Scrape
    raw = scraper.scrape_all()
    if not raw:
        log.warning("No jobs scraped — check portal connectivity")
        return []

    # 2. Filter
    filtered = filters.apply_filters(raw)
    if not filtered:
        log.warning("All jobs filtered out")
        return []

    # 3. Dedup against DB
    new_jobs = tracker.filter_new(filtered)
    if not new_jobs:
        log.info("No new jobs since last run")
        return []

    # 4. Score
    scored = scorer.score_all(new_jobs)

    # 5. Save to DB
    tracker.save(scored)

    # 6. Export CSV
    csv_path = os.path.join(OUTPUT_DIR, f"jobs_{stamp}.csv")
    export_csv(scored, csv_path)

    # 7. Email digest
    if notify:
        sent = notifier.send_digest(scored)
        if sent:
            notify_ids = [j["id"] for j in scored if j["score"] >= SCORE_MIN_NOTIFY]
            tracker.mark_notified(notify_ids)

    top     = [j for j in scored if j["score"] >= SCORE_MIN_NOTIFY]
    opt_pos = [j for j in top if j.get("opt_friendly")]
    log.info("-" * 60)
    log.info("Done: %d new  |  %d above threshold  |  %d OPT-positive",
             len(scored), len(top), len(opt_pos))
    log.info("Output: %s", csv_path)
    return scored


if __name__ == "__main__":
    no_notify = "--no-notify" in sys.argv
    run(notify=not no_notify)
