"""Send HTML email digest of top OPT-friendly DevOps jobs."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from config import GMAIL_USER, GMAIL_APP_PASSWORD, NOTIFY_EMAIL, SCORE_MIN_NOTIFY

log = logging.getLogger(__name__)


def _opt_badge(job: dict) -> str:
    if job.get("opt_friendly"):
        return '<span style="background:#22c55e;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">OPT Friendly</span>'
    return '<span style="background:#94a3b8;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">Check Visa</span>'


def _score_color(score: int) -> str:
    if score >= 70:
        return "#16a34a"
    if score >= 50:
        return "#d97706"
    return "#dc2626"


def _job_row(job: dict) -> str:
    score_color = _score_color(job["score"])
    opt_badge   = _opt_badge(job)
    location    = "🌐 Remote/Hybrid" if job.get("is_remote") else job.get("location", "")
    return f"""
    <tr style="border-bottom:1px solid #e2e8f0;">
      <td style="padding:10px 8px;">
        <a href="{job['url']}" style="color:#2563eb;text-decoration:none;font-weight:600;">
          {job['title']}
        </a><br>
        <small style="color:#64748b;">{job['company']} · {location} · {job['portal'].title()}</small><br>
        {opt_badge}
      </td>
      <td style="padding:10px 8px;white-space:nowrap;">
        <strong style="color:{score_color};">{job['score']}/100</strong>
      </td>
      <td style="padding:10px 8px;color:#64748b;font-size:12px;">
        {job.get('posted_date','')[:10]}
      </td>
    </tr>"""


def build_html(jobs: list[dict]) -> str:
    today        = datetime.now().strftime("%B %d, %Y")
    opt_count    = sum(1 for j in jobs if j.get("opt_friendly"))
    remote_count = sum(1 for j in jobs if j.get("is_remote"))

    by_type: dict[str, list[dict]] = {}
    for j in jobs:
        by_type.setdefault(j["job_type"], []).append(j)

    sections = ""
    for jtype, type_jobs in sorted(by_type.items(), key=lambda x: -max(j["score"] for j in x[1])):
        rows = "".join(_job_row(j) for j in type_jobs)
        sections += f"""
        <h3 style="color:#1e293b;margin:24px 0 8px;border-left:4px solid #2563eb;padding-left:10px;">
          {jtype} <small style="color:#64748b;font-size:14px;">({len(type_jobs)} jobs)</small>
        </h3>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;font-family:sans-serif;font-size:14px;">
          <thead>
            <tr style="background:#f1f5f9;color:#475569;font-size:12px;text-transform:uppercase;">
              <th style="padding:8px;text-align:left;">Job</th>
              <th style="padding:8px;text-align:left;">Score</th>
              <th style="padding:8px;text-align:left;">Posted</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    return f"""
    <html><body style="font-family:sans-serif;background:#f8fafc;padding:20px;">
    <div style="max-width:800px;margin:auto;background:#fff;border-radius:8px;
                padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1);">
      <h2 style="color:#1e293b;margin:0 0 4px;">
        OPT DevOps Job Digest — {today}
      </h2>
      <p style="color:#64748b;margin:0 0 20px;font-size:14px;">
        {len(jobs)} new jobs &nbsp;|&nbsp;
        <span style="color:#22c55e;">✓ {opt_count} OPT-friendly</span> &nbsp;|&nbsp;
        {remote_count} remote/hybrid
      </p>
      {sections}
      <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
      <p style="color:#94a3b8;font-size:11px;text-align:center;">
        opt_jobscraper · Entry &amp; mid-level DevOps for OPT/F-1 students in the US
      </p>
    </div>
    </body></html>"""


def send_digest(jobs: list[dict]) -> bool:
    eligible = [j for j in jobs if j["score"] >= SCORE_MIN_NOTIFY]
    if not eligible:
        log.info("Notifier: no jobs above score threshold %d", SCORE_MIN_NOTIFY)
        return False
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        log.warning("Notifier: email credentials not set — skipping send")
        return False

    html = build_html(eligible)
    msg  = MIMEMultipart("alternative")
    msg["Subject"] = f"[OPT Jobs] {len(eligible)} new DevOps opportunities"
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        log.info("Notifier: sent digest (%d jobs) to %s", len(eligible), NOTIFY_EMAIL)
        return True
    except Exception as exc:
        log.error("Notifier: send failed — %s", exc)
        return False
