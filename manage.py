#!/usr/bin/env python3
"""
My Apps — Unified Control Center
─────────────────────────────────────────────────────────────────────────────
Manage all apps from one place. No need to cd into each directory.

USAGE
  python3 manage.py                         # show status dashboard
  python3 manage.py status                  # same as above
  python3 manage.py start                   # start ALL web apps
  python3 manage.py stop                    # stop  ALL web apps
  python3 manage.py restart                 # restart ALL web apps
  python3 manage.py open                    # open all running web apps in browser

  python3 manage.py start  resumechecker    # start specific app
  python3 manage.py stop   expenses         # stop  specific app
  python3 manage.py restart expenses        # restart specific app
  python3 manage.py status  resumechecker   # status of one app
  python3 manage.py logs   resumechecker    # tail logs
  python3 manage.py open   expenses         # open in browser

  python3 manage.py run jobscraper-portals  # run a one-shot script (foreground)
  python3 manage.py run jobscraper-vendors
  python3 manage.py run opt-scraper
"""

import os, sys, signal, subprocess, time, webbrowser, textwrap
from pathlib import Path

BASE = Path(__file__).parent.resolve()

# ── ANSI colours ──────────────────────────────────────────────────────────────
R  = "\033[31m"; G  = "\033[32m"; Y  = "\033[33m"
B  = "\033[34m"; M  = "\033[35m"; C  = "\033[36m"
W  = "\033[37m"; DIM= "\033[2m";  BOLD="\033[1m"; RST= "\033[0m"

def ok(msg):   print(f"{G}✓{RST}  {msg}")
def err(msg):  print(f"{R}✗{RST}  {msg}")
def info(msg): print(f"{B}→{RST}  {msg}")
def warn(msg): print(f"{Y}!{RST}  {msg}")
def hdr(msg):  print(f"\n{BOLD}{msg}{RST}")

# ── App registry ──────────────────────────────────────────────────────────────
#
#  type "web"    → long-running Flask server managed via PID file
#  type "script" → one-shot task run in foreground via `manage.py run <name>`
#
APPS: dict[str, dict] = {
    "resumechecker": {
        "label":  "ResumeChecker",
        "desc":   "ATS resume scorer — any JD, any role",
        "dir":    BASE / "Scorer",
        "cmd":    [sys.executable, "app.py"],
        "port":   5055,
        "url":    "http://resumechecker:5055",
        "type":   "web",
        "env":    {},
    },
    "expenses": {
        "label":  "Expenses Tracker",
        "desc":   "Personal expense tracking & categorisation",
        "dir":    BASE / "Expenses",
        "cmd":    [sys.executable, "app.py"],
        "port":   5050,
        "url":    "http://rupeexpenses:5050",
        "type":   "web",
        "env":    {"EXPENSES_DEBUG": "0"},
    },
    "jobscraper-portals": {
        "label":  "Job Scraper — Portals",
        "desc":   "Scrape LinkedIn / Indeed / Dice / Monster",
        "dir":    BASE / "Job_scraper",
        "cmd":    [sys.executable, "run_portals.py"],
        "port":   None,
        "url":    None,
        "type":   "script",
        "env":    {},
    },
    "jobscraper-vendors": {
        "label":  "Job Scraper — Vendors",
        "desc":   "Scrape vendor / staffing agency sites",
        "dir":    BASE / "Job_scraper",
        "cmd":    [sys.executable, "run_vendors.py"],
        "port":   None,
        "url":    None,
        "type":   "script",
        "env":    {},
    },
    "opt-scraper": {
        "label":  "Optimised Job Scraper",
        "desc":   "Full pipeline: scrape → score → notify",
        "dir":    BASE / "opt_jobscraper",
        "cmd":    ["bash", "run.sh"],
        "port":   None,
        "url":    None,
        "type":   "script",
        "env":    {},
    },
}

WEB_APPS    = [k for k, v in APPS.items() if v["type"] == "web"]
SCRIPT_APPS = [k for k, v in APPS.items() if v["type"] == "script"]

# ── PID / log helpers ─────────────────────────────────────────────────────────

def _pid_path(name: str) -> Path:
    return APPS[name]["dir"] / ".pid"

def _log_path(name: str) -> Path:
    log_dir = APPS[name]["dir"] / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "app.log"

def _read_pid(name: str) -> int | None:
    try:
        return int(_pid_path(name).read_text().strip())
    except Exception:
        return None

def _is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def _port_pids(port: int) -> list[int]:
    """Return all PIDs listening on the given TCP port (handles werkzeug reloader)."""
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}"], stderr=subprocess.DEVNULL
        ).decode().strip()
        return [int(p) for p in out.splitlines() if p.strip().isdigit()]
    except Exception:
        return []

def _status(name: str) -> tuple[bool, int | None]:
    """Check if a web app is running — via PID file first, then port scan fallback."""
    app  = APPS[name]
    pid  = _read_pid(name)
    alive = _is_alive(pid)

    if not alive:
        # Clean up stale PID file
        if _pid_path(name).exists():
            _pid_path(name).unlink(missing_ok=True)
        pid = None
        # Fallback: detect processes started outside manage.py by scanning the port
        if app.get("port"):
            pids = _port_pids(app["port"])
            if pids:
                pid   = pids[0]
                alive = True

    return alive, pid

# ── Web app lifecycle ─────────────────────────────────────────────────────────

def start_web(name: str) -> bool:
    app = APPS[name]
    alive, pid = _status(name)
    if alive:
        info(f"{app['label']}  already running  (PID {pid})  →  {app['url']}")
        # Write PID file if it was missing (app started outside manage.py)
        if pid and not _pid_path(name).exists():
            _pid_path(name).write_text(str(pid))
        return True

    log = _log_path(name)
    log_fd = open(log, "a")
    env = {**os.environ, **app["env"]}

    proc = subprocess.Popen(
        app["cmd"],
        stdout=log_fd, stderr=log_fd,
        cwd=app["dir"],
        env=env,
    )
    _pid_path(name).write_text(str(proc.pid))

    # Wait up to 4 s for the server to start accepting connections
    started = False
    for _ in range(20):
        time.sleep(0.2)
        if not _is_alive(proc.pid):
            break
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{app['port']}/", timeout=1)
            started = True
            break
        except Exception:
            pass

    if _is_alive(proc.pid):
        ok(f"{app['label']}  started  (PID {proc.pid})  →  {app['url']}")
        info(f"Logs: {log}")
        return True
    else:
        err(f"{app['label']}  failed to start — check {log}")
        return False


def stop_web(name: str) -> bool:
    app = APPS[name]
    alive, pid = _status(name)
    if not alive:
        info(f"{app['label']}  not running")
        return True

    # Collect ALL pids on the port (werkzeug reloader spawns a child)
    port_pids = _port_pids(app["port"]) if app.get("port") else []
    all_pids  = list({pid} | set(port_pids)) if pid else port_pids

    for p in all_pids:
        try:
            os.kill(p, signal.SIGTERM)
        except ProcessLookupError:
            pass

    for _ in range(30):
        time.sleep(0.2)
        if not any(_is_alive(p) for p in all_pids):
            break

    for p in all_pids:
        if _is_alive(p):
            try:
                os.kill(p, signal.SIGKILL)
            except ProcessLookupError:
                pass
    time.sleep(0.3)

    _pid_path(name).unlink(missing_ok=True)
    ok(f"{app['label']}  stopped  (was PID {pid})")
    return True


def restart_web(name: str):
    app = APPS[name]
    info(f"Restarting  {app['label']} …")
    stop_web(name)
    time.sleep(0.4)
    start_web(name)


def logs_web(name: str):
    log = _log_path(name)
    if not log.exists():
        info("No log file yet — start the app first")
        return
    app = APPS[name]
    info(f"Tailing logs for  {app['label']}  ({log})  — Ctrl-C to stop\n")
    try:
        subprocess.run(["tail", "-f", "-n", "80", str(log)])
    except KeyboardInterrupt:
        print()


def open_web(name: str):
    app = APPS[name]
    alive, _ = _status(name)
    if not alive:
        info(f"Not running — starting {app['label']} first …")
        if not start_web(name):
            return
        time.sleep(1)
    webbrowser.open(app["url"])
    ok(f"Opened  {app['url']}")

# ── Script runner ─────────────────────────────────────────────────────────────

def run_script(name: str):
    app = APPS[name]
    info(f"Running  {app['label']} …  (Ctrl-C to abort)\n")
    env = {**os.environ, **app["env"]}
    try:
        result = subprocess.run(
            app["cmd"],
            cwd=app["dir"],
            env=env,
        )
        if result.returncode == 0:
            ok(f"{app['label']}  finished  (exit 0)")
        else:
            err(f"{app['label']}  exited with code {result.returncode}")
    except KeyboardInterrupt:
        warn(f"\n{app['label']}  aborted by user")

# ── Status dashboard ──────────────────────────────────────────────────────────

def _dot(alive: bool) -> str:
    return f"{G}●{RST}" if alive else f"{DIM}○{RST}"

def cmd_status(target: str | None = None):
    names = ([target] if target else list(APPS.keys()))

    # Header
    print(f"\n{BOLD}{'─'*62}{RST}")
    print(f"  {BOLD}My Apps — Control Center{RST}")
    print(f"{BOLD}{'─'*62}{RST}")
    print(f"  {'APP':<22} {'TYPE':<8} {'STATUS':<14} {'PID':<8} URL / INFO")
    print(f"  {'─'*22} {'─'*8} {'─'*14} {'─'*8} {'─'*20}")

    for name in names:
        if name not in APPS:
            err(f"Unknown app: {name}")
            continue
        app = APPS[name]
        if app["type"] == "web":
            alive, pid = _status(name)
            status_str = (f"{G}RUNNING{RST}" if alive else f"{DIM}stopped{RST}")
            pid_str    = str(pid) if alive else "—"
            url_str    = app["url"] or "—"
        else:
            alive = False
            status_str = f"{C}script{RST}"
            pid_str    = "—"
            url_str    = "run via: manage.py run " + name

        dot = _dot(alive)
        print(f"  {dot} {app['label']:<21} {app['type']:<8} {status_str:<22} {pid_str:<8} {DIM}{url_str}{RST}")

    print(f"{BOLD}{'─'*62}{RST}")
    print(f"  {DIM}Tip: python3 manage.py start | stop | restart | logs | open{RST}\n")

# ── Command dispatch ──────────────────────────────────────────────────────────

def _resolve(target: str | None, allowed_types=("web",)) -> list[str]:
    """Return list of app names matching target. Error and exit if invalid."""
    if target:
        if target not in APPS:
            err(f"Unknown app: '{target}'")
            print(f"  Available: {', '.join(APPS)}")
            sys.exit(1)
        if APPS[target]["type"] not in allowed_types:
            err(f"'{target}' is a {APPS[target]['type']} — use 'run' instead")
            sys.exit(1)
        return [target]
    return [k for k in APPS if APPS[k]["type"] in allowed_types]


def main():
    args = sys.argv[1:]
    cmd  = args[0].lower() if args else "status"
    tgt  = args[1].lower() if len(args) > 1 else None

    if cmd == "status":
        cmd_status(tgt)

    elif cmd == "start":
        for name in _resolve(tgt):
            start_web(name)

    elif cmd == "stop":
        for name in _resolve(tgt):
            stop_web(name)

    elif cmd == "restart":
        for name in _resolve(tgt):
            restart_web(name)

    elif cmd == "logs":
        if not tgt:
            err("Specify an app:  python3 manage.py logs <app>")
            print(f"  Web apps: {', '.join(WEB_APPS)}")
            sys.exit(1)
        names = _resolve(tgt)
        logs_web(names[0])

    elif cmd == "open":
        for name in _resolve(tgt):
            open_web(name)

    elif cmd == "run":
        if not tgt:
            err("Specify a script:  python3 manage.py run <script>")
            print(f"  Scripts: {', '.join(SCRIPT_APPS)}")
            sys.exit(1)
        if tgt not in APPS or APPS[tgt]["type"] != "script":
            err(f"'{tgt}' is not a runnable script app")
            print(f"  Scripts: {', '.join(SCRIPT_APPS)}")
            sys.exit(1)
        run_script(tgt)

    else:
        print(textwrap.dedent(f"""
        {BOLD}My Apps — Unified Control Center{RST}

        Usage:
          python3 manage.py                           show status dashboard
          python3 manage.py status [app]              status of all or one app
          python3 manage.py start  [app]              start all web apps or one
          python3 manage.py stop   [app]              stop  all web apps or one
          python3 manage.py restart [app]             restart all or one
          python3 manage.py logs   <app>              tail app log
          python3 manage.py open   [app]              open in browser
          python3 manage.py run    <script>           run a one-shot script

        Web apps:    {', '.join(WEB_APPS)}
        Scripts:     {', '.join(SCRIPT_APPS)}
        """).strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
