"""
Send email digest of all unsent jobs already in the DB.
Usage:
    python3 send_digest.py          # send jobs above SCORE_MIN_NOTIFY threshold
    python3 send_digest.py --all    # send every saved job regardless of score
    python3 send_digest.py --rescore  # re-score zero-scored jobs then send
"""
import logging
import sys

from config import SCORE_MIN_NOTIFY
import tracker
import notifier
import scorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("JobSpy").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# Re-score jobs that were saved with score=0 (pipeline interrupted / old bug)
if "--rescore" in sys.argv or True:   # always rescore — safe because UPSERT only updates if better
    updated = tracker.rescore_all(scorer.score_job)
    log.info("Re-scored %d previously zero-scored jobs", updated)

min_score = 0 if "--all" in sys.argv else SCORE_MIN_NOTIFY

jobs = tracker.unnotified(min_score=min_score)
if not jobs:
    log.info("No unsent jobs in DB above score=%d. Run pipeline.py to scrape new jobs.", min_score)
    sys.exit(0)

log.info("Sending digest of %d jobs (min_score=%d)...", len(jobs), min_score)
sent = notifier.send_digest(jobs)

if sent:
    notify_ids = [j["id"] for j in jobs]
    tracker.mark_notified(notify_ids)
    log.info("Done — digest sent to %s and jobs marked notified.", notifier.NOTIFY_EMAIL)
else:
    log.error("Send failed — check Gmail credentials in .env")
