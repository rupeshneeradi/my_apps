#!/usr/bin/env python3
"""
Vendor Pipeline Runner — v1.0.6
Schedule: Monday & Thursday at 6:50 AM
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import VERSION
from ats_scorer import score_job
from drive_resumes import load_resumes, load_resume_docx
from email_notifier import send_digest, send_error, send_run_start, send_run_stop
from filters import apply_filters
from resume_tailor import tailor_all
from tracker import load_sheet_ids, mark_applied_dates, write_jobs
from vendor_scraper import scrape_vendors

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/vendor_pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("run_vendors")
PIPELINE = "Vendor Pipeline"


def main():
    log.info("=" * 60)
    log.info("Job Pipeline v%s — %s starting", VERSION, PIPELINE)
    log.info("=" * 60)

    send_run_start(PIPELINE)

    try:
        log.info("Loading resumes from Google Drive...")
        resumes = load_resumes()
        if not resumes:
            log.warning("No resumes loaded — ATS scores will be empty")

        # Auto-fill Applied Date for any rows the user marked Applied since last run
        dated = mark_applied_dates()
        if dated:
            log.info("Auto-filled applied date on %d rows", dated)
        known_ids, applied_ids = load_sheet_ids()   # single API call

        log.info("Scraping vendor job portals...")
        raw_jobs = scrape_vendors()
        log.info("Total raw jobs scraped: %d", len(raw_jobs))

        # Filter: relevance (Oracle/ETL roles only) + contract type (C2C/1099/etc.)
        jobs, filter_stats = apply_filters(raw_jobs)
        log.info(
            "After filters — relevant: %d, contract-type: %d (dropped relevance: %d, contract: %d)",
            filter_stats["after_relevance"], filter_stats["after_contract"],
            filter_stats["dropped_relevance"], filter_stats["dropped_contract"],
        )

        # Remove already-applied
        jobs = [j for j in jobs if j["id"] not in applied_ids]
        log.info("After removing applied: %d", len(jobs))

        # Score every job — selects best resume + shows matched/missing keywords
        log.info("Scoring jobs against resumes...")
        for j in jobs:
            j["ats_result"] = score_job(j, resumes)

        # Generate tailored resume DOCX for each qualifying job
        log.info("Generating tailored resumes...")
        resume_docx = load_resume_docx()
        tailored = tailor_all(jobs, resume_docx)
        log.info("Tailored resumes generated: %d", tailored)

        qualifying = jobs
        log.info("Jobs to email/track: %d", len(qualifying))

        new_count = write_jobs(qualifying, known_ids=known_ids)
        send_digest(PIPELINE, qualifying, filter_stats)
        send_run_stop(PIPELINE, total=len(raw_jobs), new=new_count, filter_stats=filter_stats)

        log.info("%s complete. %d jobs / %d new.", PIPELINE, len(qualifying), new_count)

    except Exception as exc:
        log.exception("Pipeline crashed: %s", exc)
        send_error(PIPELINE, exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
