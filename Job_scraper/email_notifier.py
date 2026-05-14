"""Gmail SMTP email sender — digest + run status notifications. v1.0.7"""
import logging
import smtplib
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    GMAIL_APP_PASSWORD, GMAIL_USER, NOTIFY_EMAIL, VERSION,
)

log = logging.getLogger(__name__)


def _send(subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = NOTIFY_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        log.info("Email sent: %s", subject)
        return True
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False


# ── Status notifications ──────────────────────────────────────────────────────

def send_run_start(pipeline: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _send(
        f"[Job Pipeline v{VERSION}] {pipeline} — Started ({ts})",
        f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:560px;padding:20px">
        <p>Pipeline <strong>{pipeline}</strong> started at <strong>{ts}</strong>.</p>
        <p style="color:#666;margin-top:8px">A digest will arrive when the run completes.</p>
        </div>""",
    )


def send_run_stop(pipeline: str, total: int, new: int, filter_stats: dict | None = None) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    fs = filter_stats or {}
    rows = f"""
    <tr><td style="padding:5px 10px">Total scraped</td><td style="padding:5px 10px"><strong>{fs.get('total_raw', total)}</strong></td></tr>
    <tr><td style="padding:5px 10px">After role relevance filter</td><td style="padding:5px 10px"><strong>{fs.get('after_relevance','—')}</strong></td></tr>
    <tr><td style="padding:5px 10px">After C2C / Contract filter</td><td style="padding:5px 10px"><strong>{fs.get('after_contract','—')}</strong></td></tr>
    <tr><td style="padding:5px 10px">New rows written to tracker</td><td style="padding:5px 10px"><strong>{new}</strong></td></tr>
    """ if fs else f"<tr><td>Total scraped</td><td>{total}</td></tr><tr><td>New to tracker</td><td>{new}</td></tr>"

    _send(
        f"[Job Pipeline v{VERSION}] {pipeline} — Completed ({new} new jobs)",
        f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:560px;padding:20px">
        <p>Pipeline <strong>{pipeline}</strong> completed at <strong>{ts}</strong>.</p>
        <table style="border-collapse:collapse;margin-top:12px;font-size:13px">
        <tr style="background:#f0f0f0">
          <th style="padding:5px 10px;text-align:left">Metric</th>
          <th style="padding:5px 10px;text-align:left">Value</th>
        </tr>
        {rows}
        </table>
        </div>""",
    )


def send_error(pipeline: str, error: Exception) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    tb = traceback.format_exc()
    _send(
        f"[Job Pipeline v{VERSION}] {pipeline} — ERROR ({ts})",
        f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:680px;padding:20px">
        <p style="color:#c62828">Pipeline <strong>{pipeline}</strong> encountered an error at <strong>{ts}</strong>.</p>
        <pre style="background:#f9f9f9;border:1px solid #ddd;padding:12px;font-size:12px;margin-top:12px;overflow:auto">{tb}</pre>
        </div>""",
    )


# ── Digest styles ─────────────────────────────────────────────────────────────
_CSS = """
body { font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #222; margin: 0; padding: 16px; background: #f5f5f5; }
.wrap { max-width: 860px; margin: 0 auto; background: #fff; border: 1px solid #ddd; }
h1 { color: #1a237e; font-size: 18px; margin: 0 0 4px; }
.run-meta { font-size: 12px; color: #777; margin-bottom: 16px; }
h2 { color: #283593; font-size: 14px; border-bottom: 2px solid #3949ab; padding-bottom: 5px; margin: 20px 0 10px; }
h3 { color: #3949ab; font-size: 13px; margin: 14px 0 6px; }
.summary { display: flex; gap: 20px; font-size: 13px; margin-bottom: 16px; flex-wrap: wrap; }
.summary span { display: flex; align-items: center; gap: 5px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.dot-hot  { background: #2e7d32; }
.dot-good { background: #1565c0; }
.dot-ok   { background: #e65100; }
.dot-gray { background: #90a4ae; }
table { border-collapse: collapse; width: 100%; margin-bottom: 14px; font-size: 13px; }
th { background: #3949ab; color: #fff; padding: 7px 9px; text-align: left; font-weight: 600; }
td { padding: 6px 9px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
tr.r-hot  td { background: #f1f8e9; }
tr.r-good td { background: #e3f2fd; }
tr.r-ok   td { background: #fff3e0; }
.badge { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; white-space: nowrap; }
a.apply { display: inline-block; padding: 2px 9px; background: #3949ab; color: #fff !important;
          text-decoration: none; border-radius: 3px; font-size: 12px; white-space: nowrap; }
.gap-cell { font-size: 11px; color: #999; }
.filter-box { font-size: 12px; color: #555; background: #f9f9f9; border: 1px solid #e0e0e0;
              padding: 8px 14px; margin-bottom: 14px; line-height: 1.7; }
.footer { font-size: 11px; color: #999; padding-top: 14px; border-top: 1px solid #e0e0e0; margin-top: 16px; }
"""


def _dot(label: str) -> str:
    cls = {"HOT": "dot-hot", "GOOD": "dot-good", "OK": "dot-ok"}.get(label, "dot-gray")
    return f'<span class="dot {cls}"></span>'


def _badge(label: str, score: float) -> str:
    return f'<span class="badge">{_dot(label)} {score:.0f}%</span>'


def _row(j: dict) -> str:
    ats      = j.get("ats_result")
    score    = ats.score if ats else 0.0
    label    = ats.label if ats else "—"
    resume   = ats.best_resume if ats else "—"
    gaps     = ", ".join(ats.missing[:6]) if ats and ats.missing else "—"
    url      = j.get("url", "") or ""
    cls      = {"HOT": "r-hot", "GOOD": "r-good", "OK": "r-ok"}.get(label, "")
    apply    = f'<a class="apply" href="{url}" target="_blank">Apply</a>' if url else "—"
    ref_key  = j.get("tailored_resume", "") or j.get("id", "")
    ref_cell = (
        f'<span style="font-family:monospace;font-size:11px;'
        f'background:#f4f4f4;padding:1px 5px;border-radius:3px;'
        f'color:#333;letter-spacing:0.02em">{ref_key}</span>'
    ) if ref_key else "—"
    return (
        f'<tr class="{cls}">'
        f'<td>{j.get("title","")}</td>'
        f'<td>{j.get("company","")}</td>'
        f'<td>{j.get("location","")}</td>'
        f'<td>{j.get("portal","")}</td>'
        f'<td>{_badge(label, score)}</td>'
        f'<td style="font-size:12px">{resume}</td>'
        f'<td>{ref_cell}</td>'
        f'<td>{apply}</td>'
        f'<td class="gap-cell">{gaps}</td>'
        f'</tr>'
    )


def _table(jobs: list[dict]) -> str:
    if not jobs:
        return '<p style="font-size:13px;color:#999;margin:4px 0 12px">No jobs in this category.</p>'
    rows = "\n".join(_row(j) for j in jobs)
    return (
        "<table>"
        "<tr><th>Title</th><th>Company</th><th>Location</th><th>Source</th>"
        "<th>Score</th><th>Resume</th><th>Key</th><th>Apply</th><th>Skill Gaps</th></tr>"
        f"{rows}</table>"
    )


def send_digest(pipeline: str, jobs: list[dict], filter_stats: dict | None = None) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    fs = filter_stats or {}

    if not jobs:
        _send(
            f"[Job Pipeline v{VERSION}] {pipeline} — No C2C/Contract jobs found — {date_str}",
            f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#555;padding:20px">
            <p>No C2C / Corp-to-Corp / Contract / 1099 jobs found this run.</p>
            <p style="font-size:12px;color:#999;margin-top:8px">
              Scraped: {fs.get('total_raw','—')} &rarr;
              Relevant: {fs.get('after_relevance','—')} &rarr;
              C2C/Contract: {fs.get('after_contract','—')}
            </p>
            </div>""",
        )
        return

    def _sort(lst):
        return sorted(lst, key=lambda j: -(j.get("ats_result") and j["ats_result"].score or 0))

    # ── Portal breakdown ──────────────────────────────────────────────────────
    ALL_PORTALS = ["LinkedIn", "Indeed", "Dice", "Monster"]
    by_portal: dict[str, list] = {}
    for j in jobs:
        by_portal.setdefault(j.get("portal", "Other"), []).append(j)

    # Portal count summary bar — shows 0 for portals with no results
    portal_counts = " &nbsp;|&nbsp; ".join(
        f"<strong>{p}</strong>: {len(by_portal.get(p, []))}"
        for p in ALL_PORTALS
    )
    # Add any non-standard portals (vendor_linkedin, etc.)
    for p in sorted(by_portal):
        if p not in ALL_PORTALS:
            portal_counts += f" &nbsp;|&nbsp; <strong>{p}</strong>: {len(by_portal[p])}"

    portal_html = ""
    for portal in ALL_PORTALS + [p for p in sorted(by_portal) if p not in ALL_PORTALS]:
        pjobs = by_portal.get(portal, [])
        if not pjobs:
            continue
        portal_html += f"<h3>{portal} ({len(pjobs)} jobs)</h3>{_table(_sort(pjobs))}"

    # ── Filter stats bar ──────────────────────────────────────────────────────
    filter_html = (
        f'<div class="filter-box">'
        f'Scraped: <strong>{fs.get("total_raw","—")}</strong>'
        f' &rarr; Role match: <strong>{fs.get("after_relevance","—")}</strong>'
        f' &rarr; C2C/Contract: <strong>{fs.get("after_contract","—")}</strong>'
        f' &rarr; Shown: <strong>{len(jobs)}</strong>'
        f'</div>'
    ) if fs else ""

    tracker_note = (
        '<p style="font-size:12px;color:#666;margin-top:10px;border-top:1px solid #eee;padding-top:8px">'
        'To apply: find <code>tailored_resumes/{Key}.docx</code> &rarr; review &amp; add missing keywords &rarr; apply. '
        'Then open Google Sheet &rarr; set <strong>Status = Applied</strong> (pipeline skips it next run &amp; records the date).'
        '</p>'
    )

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>{_CSS}</style></head>
<body><div class="wrap" style="padding:20px">

<h1>Job Pipeline Digest &mdash; {pipeline}</h1>
<div class="run-meta">v{VERSION} &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp; C2C / Corp-to-Corp / C2H / 1099 / Contract only</div>

<div class="filter-box" style="margin-bottom:10px">
  Portal results: {portal_counts}
</div>

{filter_html}

<h2>Jobs by Portal &mdash; {len(jobs)} total</h2>
{portal_html}

{tracker_note}

<div class="footer">
  Job Pipeline v{VERSION} &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp;
  Score shown for resume selection only &mdash; all C2C/Contract jobs are listed
</div>

</div></body></html>"""

    _send(
        f"[Job Pipeline v{VERSION}] {pipeline} — {len(jobs)} C2C/Contract jobs — {date_str}",
        html,
    )
