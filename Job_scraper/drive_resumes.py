"""
Download and extract text from resumes stored in Google Drive.
v1.0.3 — Added:
  • 30-second SSL/HTTP timeout via httplib2
  • 3-attempt retry with backoff on any network error
  • Local disk cache (resume_cache/) so Drive outages don't kill the pipeline
"""
import io
import json
import logging
import os
import re
import time

import httplib2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import PyPDF2
from docx import Document

from config import GDRIVE_FOLDER_ID, GDRIVE_CREDS_FILE

log = logging.getLogger(__name__)

SCOPES          = ["https://www.googleapis.com/auth/drive.readonly"]
CACHE_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume_cache")
DOCX_CACHE_DIR  = os.path.join(CACHE_DIR, "docx")   # raw DOCX binaries for resume_tailor
CONNECT_TIMEOUT = 30    # seconds for SSL handshake + connect
MAX_RETRIES     = 3
RETRY_DELAY     = 5     # seconds between retries

_MEMORY_CACHE:      dict[str, str]   = {}   # filename → extracted text
_DOCX_MEMORY_CACHE: dict[str, bytes] = {}   # filename → raw DOCX bytes


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_service():
    creds = Credentials.from_service_account_file(GDRIVE_CREDS_FILE, scopes=SCOPES)
    # Pass an httplib2 Http object with an explicit timeout so SSL hangs don't
    # block forever (default is no timeout → hangs indefinitely on bad networks)
    http = httplib2.Http(timeout=CONNECT_TIMEOUT)
    authed_http = google_auth_httplib2_request(creds, http)   # patched below
    return build("drive", "v3", credentials=creds,
                 requestBuilder=_build_request_with_timeout,
                 cache_discovery=False)


def _build_request_with_timeout(http, *args, **kwargs):
    """Inject a timeout into every httplib2 request made by the API client."""
    import googleapiclient.http as ghttp
    new_http = httplib2.Http(timeout=CONNECT_TIMEOUT)
    return ghttp.HttpRequest(new_http, *args, **kwargs)


def _retry(fn, label: str):
    """Call fn() up to MAX_RETRIES times; raise on final failure."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            log.warning("  [attempt %d/%d] %s failed: %s", attempt, MAX_RETRIES, label, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)   # 5s, 10s
    raise last_exc


# ── local disk cache ──────────────────────────────────────────────────────────

def _disk_cache_path(filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = re.sub(r"[^\w\-.]", "_", filename)
    return os.path.join(CACHE_DIR, safe + ".txt")


def _save_to_disk(filename: str, text: str) -> None:
    try:
        with open(_disk_cache_path(filename), "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        log.warning("Disk cache write failed for %s: %s", filename, e)


def _save_docx_bytes(filename: str, data: bytes) -> None:
    """Cache raw DOCX binary so resume_tailor can clone without re-downloading."""
    if not filename.lower().endswith(".docx"):
        return
    try:
        os.makedirs(DOCX_CACHE_DIR, exist_ok=True)
        path = os.path.join(DOCX_CACHE_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        log.warning("DOCX binary cache write failed for %s: %s", filename, e)


def load_resume_docx() -> dict[str, bytes]:
    """
    Return {filename: bytes} for all cached DOCX files.
    Used by resume_tailor.py to clone base resumes.
    Falls back to disk cache if in-memory cache is empty.
    """
    global _DOCX_MEMORY_CACHE
    if _DOCX_MEMORY_CACHE:
        return _DOCX_MEMORY_CACHE
    result: dict[str, bytes] = {}
    if os.path.isdir(DOCX_CACHE_DIR):
        for fname in os.listdir(DOCX_CACHE_DIR):
            if fname.lower().endswith(".docx"):
                try:
                    with open(os.path.join(DOCX_CACHE_DIR, fname), "rb") as f:
                        result[fname] = f.read()
                except Exception as e:
                    log.warning("DOCX binary cache read failed for %s: %s", fname, e)
    if result:
        log.info("Loaded %d DOCX binaries from disk cache", len(result))
    _DOCX_MEMORY_CACHE = result
    return result


def _load_from_disk() -> dict[str, str]:
    """Load all cached resume texts from disk — used as fallback when Drive is down."""
    cache: dict[str, str] = {}
    if not os.path.isdir(CACHE_DIR):
        return cache
    for fname in os.listdir(CACHE_DIR):
        if not fname.endswith(".txt"):
            continue
        # Strip the .txt suffix we added; reconstruct original name
        orig = fname[:-4]   # e.g. "Roopesh_ETL.docx.txt" → "Roopesh_ETL.docx"
        try:
            with open(os.path.join(CACHE_DIR, fname), encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                cache[orig] = text
        except Exception as e:
            log.warning("Disk cache read failed for %s: %s", fname, e)
    return cache


# ── text extraction ───────────────────────────────────────────────────────────

def _extract_pdf(data: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        log.warning("PDF extraction error: %s", e)
        return ""


def _extract_docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        log.warning("DOCX extraction error: %s", e)
        return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower().strip()


# ── main entry ────────────────────────────────────────────────────────────────

def load_resumes(force_reload: bool = False) -> dict[str, str]:
    """
    Return {filename: cleaned_text} for all PDF/DOCX files in the Drive folder.

    On network errors:
      - Retries up to 3 times with 5-second backoff
      - Falls back to locally cached copies if Drive is still unreachable
    """
    global _MEMORY_CACHE
    if _MEMORY_CACHE and not force_reload:
        return _MEMORY_CACHE

    if not GDRIVE_FOLDER_ID:
        log.error("GDRIVE_FOLDER_ID not set — trying disk cache")
        fallback = _load_from_disk()
        if fallback:
            log.info("Using %d cached resumes from disk", len(fallback))
            _MEMORY_CACHE = fallback
        return _MEMORY_CACHE

    # ── Build the Drive service with retry ────────────────────────────────────
    try:
        creds = Credentials.from_service_account_file(GDRIVE_CREDS_FILE, scopes=SCOPES)
        svc   = _retry(
            lambda: build("drive", "v3", credentials=creds, cache_discovery=False),
            "Drive auth",
        )
    except Exception as e:
        log.error("Google Drive auth failed after %d attempts: %s", MAX_RETRIES, e)
        fallback = _load_from_disk()
        if fallback:
            log.warning("Using %d disk-cached resumes (Drive unavailable)", len(fallback))
            _MEMORY_CACHE = fallback
        return _MEMORY_CACHE

    # ── List files ────────────────────────────────────────────────────────────
    query = (
        f"'{GDRIVE_FOLDER_ID}' in parents "
        "and mimeType != 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    try:
        results = _retry(
            lambda: svc.files().list(q=query, fields="files(id, name, mimeType)").execute(),
            "Drive list",
        )
    except Exception as e:
        log.error("Drive file listing failed: %s — falling back to disk cache", e)
        fallback = _load_from_disk()
        if fallback:
            log.warning("Using %d disk-cached resumes", len(fallback))
            _MEMORY_CACHE = fallback
        return _MEMORY_CACHE

    files = results.get("files", [])
    log.info("Found %d files in Drive folder", len(files))

    # ── Download and extract each resume ──────────────────────────────────────
    cache: dict[str, str] = {}
    for f in files:
        name = f["name"]
        fid  = f["id"]
        if not (name.lower().endswith(".pdf") or name.lower().endswith(".docx")):
            continue
        try:
            def _download(file_id=fid):
                req = svc.files().get_media(fileId=file_id)
                buf = io.BytesIO()
                dl  = MediaIoBaseDownload(buf, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
                return buf.getvalue()

            data    = _retry(_download, f"download {name}")
            text    = _extract_pdf(data) if name.lower().endswith(".pdf") else _extract_docx(data)
            cleaned = _clean(text)
            if cleaned:
                cache[name] = cleaned
                _save_to_disk(name, cleaned)       # persist text to disk cache
                if name.lower().endswith(".docx"):
                    _save_docx_bytes(name, data)   # persist binary for resume_tailor
                    _DOCX_MEMORY_CACHE[name] = data
                log.info("  Loaded: %s (%d chars)", name, len(cleaned))
        except Exception as e:
            log.warning("  Failed to load %s after retries: %s", name, e)
            # Try disk fallback for this specific file
            disk = _load_from_disk()
            if name in disk:
                cache[name] = disk[name]
                log.info("  Using disk cache for %s", name)

    if not cache:
        log.warning("No resumes loaded from Drive — trying full disk cache")
        cache = _load_from_disk()

    _MEMORY_CACHE = cache
    log.info("Total resumes ready: %d", len(cache))
    return cache
