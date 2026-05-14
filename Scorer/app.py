"""ATS + Recruiter Resume Scorer — rule-based, no AI API needed."""
import sys, os, logging, re

JOB_SCRAPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Job_scraper")
sys.path.insert(0, JOB_SCRAPER_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests as _requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, send_file
import io

from ats_scorer import score_resume
from drive_resumes import load_resumes
from analyzer import analyze
from writer import generate_resume_content
from scraper import fetch_real_examples
from docx_report import generate_report_docx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
_resumes: dict[str, str] = {}

JD_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get_resumes(force=False):
    global _resumes
    if not _resumes or force:
        _resumes = load_resumes(force_reload=force)
    return _resumes


# ── JD text extraction from URL ───────────────────────────────────────────────

def _extract_jd_from_url(url: str) -> str:
    """
    Fetch a job posting URL and return the JD text.
    Handles Indeed, LinkedIn (best-effort), and generic job boards.
    """
    try:
        resp = _requests.get(url, headers=JD_FETCH_HEADERS, timeout=12, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        raise ValueError(f"Could not fetch URL: {exc}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strip noise
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "form", "iframe", "noscript", "aside"]):
        tag.decompose()

    # Try known selectors in priority order
    SELECTORS = [
        # Indeed
        '[data-testid="jobsearch-jobDescriptionText"]',
        ".jobsearch-JobComponent-description",
        "#jobDescriptionText",
        # LinkedIn
        ".description__text",
        ".show-more-less-html",
        '[data-tracking-control-name="public_jobs_description"]',
        # Workday / Greenhouse / Lever / generic
        '[data-automation-id="jobPostingDescription"]',
        "#job-description",
        ".job-description",
        ".job_description",
        ".jobDescription",
        "article",
        "main",
        '[role="main"]',
    ]

    for sel in SELECTORS:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n").strip()
            if len(text) > 200:
                return text

    # Last resort: full visible text
    text = soup.get_text(separator="\n").strip()
    # Trim blank lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/resumes")
def list_resumes():
    force = request.args.get("reload") == "1"
    try:
        r = _get_resumes(force=force)
        return jsonify({"count": len(r), "names": sorted(r.keys())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fetch-jd", methods=["POST"])
def fetch_jd():
    """Fetch JD text from a job posting URL."""
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        text = _extract_jd_from_url(url)
        if len(text) < 100:
            return jsonify({"error": "Could not extract job description from this URL. "
                                     "Try copying and pasting the JD text directly."}), 400
        return jsonify({"text": text, "length": len(text)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log.warning("JD fetch error for %s: %s", url, e)
        return jsonify({"error": "Failed to fetch JD. Some sites (e.g. LinkedIn) "
                                 "require login — paste the JD text directly instead."}), 400


@app.route("/api/score", methods=["POST"])
def score():
    data        = request.get_json(silent=True) or {}
    jd_text     = (data.get("jd_text")     or "").strip()
    jd_title    = (data.get("jd_title")    or "").strip()
    resume_name = (data.get("resume_name") or "").strip()   # "" = score all

    if not jd_text:
        return jsonify({"error": "Job description text is required."}), 400

    try:
        resumes = _get_resumes()
    except Exception as e:
        return jsonify({"error": f"Could not load resumes: {e}"}), 500

    if not resumes:
        return jsonify({"error": "No resumes found. Check Google Drive connection."}), 500

    # Filter to a single resume if requested
    if resume_name:
        if resume_name not in resumes:
            return jsonify({"error": f"Resume '{resume_name}' not found."}), 404
        resumes = {resume_name: resumes[resume_name]}

    results = []
    for fname, rtext in resumes.items():
        ats_val, matched, missing = score_resume(rtext, jd_text, jd_title=jd_title)
        analysis       = analyze(rtext, fname, jd_text, jd_title, ats_val, matched, missing)
        resume_content = generate_resume_content(
            missing, matched, jd_title,
            analysis["signals"], analysis["gap_breakdown"], rtext
        )
        real_examples  = fetch_real_examples(missing, matched, max_per_keyword=2)
        results.append({
            "resume":         fname,
            **analysis,
            "resume_content": resume_content,
            "real_examples":  real_examples,
        })

    results.sort(key=lambda r: (r["recruiter_score"], r["ats_score"]), reverse=True)
    return jsonify({"results": results, "total": len(results), "jd_title": jd_title})


@app.route("/api/download", methods=["POST"])
def download_report():
    """
    Generate and return a .docx improvement report.
    Accepts the same result dict that /api/score returns for one resume.
    """
    data = request.get_json(silent=True) or {}
    resume_name    = data.get("resume_name", "resume")
    jd_title       = data.get("jd_title", "")
    analysis       = data.get("analysis", {})
    resume_content = data.get("resume_content", {})
    real_examples  = data.get("real_examples", {})

    try:
        docx_bytes = generate_report_docx(
            resume_name, jd_title, analysis, resume_content, real_examples
        )
    except Exception as e:
        log.error("DOCX generation failed: %s", e)
        return jsonify({"error": f"Could not generate report: {e}"}), 500

    safe_name = re.sub(r"[^\w\-.]", "_", resume_name.replace(".docx", ""))
    filename  = f"{safe_name}_improvement_report.docx"

    return send_file(
        io.BytesIO(docx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5055, host="0.0.0.0")
