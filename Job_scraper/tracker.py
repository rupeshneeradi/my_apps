"""
Google Sheets tracker — stores every scraped job, tracks applied status. v1.0.8
Sheet name: "Jobs"

Columns (17 total):
  ID | Title | Company | Location | Posted Date | Scraped Date | Portal | Job Type |
  URL | ATS Score | Best Resume | Matched KW | Missing KW | Tailored Resume |
  Status | Notes | Applied Date

  Tailored Resume = "{job_id}.docx" — find it in the tailored_resumes/ folder.
  Use it as-is or add the "Missing KW" terms before applying.
"""
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from config import GSHEET_SPREADSHEET_ID, GSHEET_CREDS_FILE

log = logging.getLogger(__name__)

SCOPES     = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Jobs"

HEADERS = [
    "ID", "Title", "Company", "Location", "Posted Date", "Scraped Date",
    "Portal", "Job Type", "URL", "ATS Score", "Best Resume",
    "Matched Keywords", "Missing Keywords",
    "Tailored Resume",          # filename in tailored_resumes/ folder
    "Status", "Notes", "Applied Date",
]

# Column indices (1-based, as gspread uses)
COL_ID              = 1
COL_TAILORED_RESUME = 14
COL_STATUS          = 15
COL_NOTES           = 16
COL_APPLIED_DATE    = 17

STATUS_NEW     = "New"
STATUS_APPLIED = "Applied"


def _connect() -> gspread.Spreadsheet:
    creds = Credentials.from_service_account_file(GSHEET_CREDS_FILE, scopes=SCOPES)
    gc    = gspread.authorize(creds)
    return gc.open_by_key(GSHEET_SPREADSHEET_ID)


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(SHEET_NAME)
        # Auto-upgrade: add any missing columns introduced in later versions
        headers = ws.row_values(1)
        if ws.col_count < len(HEADERS):
            ws.resize(rows=ws.row_count, cols=len(HEADERS))
        for col_idx, col_name in enumerate(HEADERS, start=1):
            if col_name not in headers:
                ws.update_cell(1, col_idx, col_name)
                log.info("Added column '%s' (col %d) to sheet", col_name, col_idx)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=5000, cols=len(HEADERS))
        ws.append_row(HEADERS)
        log.info("Created sheet '%s'", SHEET_NAME)
    return ws


def mark_applied_dates() -> int:
    """
    Scan sheet for rows where Status=Applied but Applied Date is empty.
    Fills Applied Date with today so the user has a record of when they applied.
    Returns count of rows updated.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        ss  = _connect()
        ws  = _get_or_create_sheet(ss)
        rows = ws.get_all_values()
        if not rows or len(rows) < 2:
            return 0

        header    = rows[0]
        data_rows = rows[1:]

        try:
            status_col = header.index("Status")
            date_col   = header.index("Applied Date")
        except ValueError:
            log.warning("Could not find Status / Applied Date columns in sheet")
            return 0

        updated = 0
        for i, row in enumerate(data_rows, start=2):   # row 2 = first data row
            status       = row[status_col].strip() if len(row) > status_col else ""
            applied_date = row[date_col].strip()   if len(row) > date_col  else ""

            if status == STATUS_APPLIED and not applied_date:
                ws.update_cell(i, date_col + 1, today)  # +1 because gspread is 1-indexed
                updated += 1

        if updated:
            log.info("Marked applied date %s on %d rows", today, updated)
        return updated

    except Exception as e:
        log.error("mark_applied_dates failed: %s", e)
        return 0


def load_applied_ids() -> set[str]:
    """Return set of job IDs already marked as Applied — these are skipped on next run."""
    try:
        ss   = _connect()
        ws   = _get_or_create_sheet(ss)
        rows = ws.get_all_records()
        ids  = {r["ID"] for r in rows if str(r.get("Status", "")).strip() == STATUS_APPLIED}
        log.info("Loaded %d applied job IDs from Sheets", len(ids))
        return ids
    except Exception as e:
        log.error("Failed to load applied IDs: %s", e)
        return set()


def load_known_ids() -> set[str]:
    """Return all job IDs in the sheet (avoids duplicate writes)."""
    try:
        ss   = _connect()
        ws   = _get_or_create_sheet(ss)
        rows = ws.get_all_records()
        return {str(r.get("ID", "")).strip() for r in rows if r.get("ID")}
    except Exception as e:
        log.error("Failed to load known IDs: %s", e)
        return set()


def load_sheet_ids() -> tuple[set[str], set[str]]:
    """
    Single API call that returns (known_ids, applied_ids).
    known_ids  = all job IDs in the sheet
    applied_ids = IDs where Status == 'Applied'
    Use this instead of calling load_known_ids() + load_applied_ids() separately.
    """
    try:
        ss   = _connect()
        ws   = _get_or_create_sheet(ss)
        rows = ws.get_all_records()
        known   = {str(r.get("ID", "")).strip() for r in rows if r.get("ID")}
        applied = {str(r.get("ID", "")).strip()
                   for r in rows
                   if str(r.get("Status", "")).strip() == STATUS_APPLIED and r.get("ID")}
        log.info("Sheet: %d total jobs, %d applied", len(known), len(applied))
        return known, applied
    except Exception as e:
        log.error("Failed to load sheet IDs: %s", e)
        return set(), set()


def write_jobs(jobs: list[dict], known_ids: set | None = None) -> int:
    """
    Append new jobs to the sheet. Returns count of rows written.
    Pass known_ids to skip a redundant API call (already fetched by caller).
    """
    if not jobs:
        log.info("write_jobs: nothing to write (empty list)")
        return 0
    try:
        ss = _connect()
        ws = _get_or_create_sheet(ss)

        # Use caller-supplied known_ids if available; otherwise fetch fresh
        if known_ids is None:
            known_ids = load_known_ids()
        log.info("write_jobs: %d qualifying jobs, %d already in sheet", len(jobs), len(known_ids))

        rows_to_add = []
        for j in jobs:
            if j["id"] in known_ids:
                log.debug("  SKIP (already in sheet): %s @ %s", j.get("title"), j.get("company"))
                continue
            ats     = j.get("ats_result")
            score   = ats.score            if ats else ""
            resume  = ats.best_resume      if ats else ""
            matched = ", ".join(ats.matched[:15]) if ats else ""
            missing = ", ".join(ats.missing[:15]) if ats else ""
            rows_to_add.append([
                j["id"],
                j.get("title", ""),
                j.get("company", ""),
                j.get("location", ""),
                j.get("posted_date", ""),
                j.get("scraped_date", ""),
                j.get("portal", ""),
                j.get("job_type", ""),
                j.get("url", ""),
                score,
                resume,
                matched,
                missing,
                j.get("tailored_resume", ""),   # e.g. "abc123def456.docx"
                STATUS_NEW,
                "",           # Notes
                "",           # Applied Date
            ])

        if rows_to_add:
            ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
            log.info("Wrote %d new jobs to Sheets", len(rows_to_add))
        else:
            log.info("write_jobs: 0 new rows — all %d qualifying jobs already in sheet", len(jobs))
        return len(rows_to_add)

    except Exception as e:
        log.error("Failed to write jobs to Sheets: %s", e, exc_info=True)
        return 0
