#!/usr/bin/env python3
"""
Expenses Tracker — management CLI
Usage:
    python3 manage.py start
    python3 manage.py stop
    python3 manage.py restart
    python3 manage.py status
    python3 manage.py open          # open in browser
    python3 manage.py logs          # tail the log file
    python3 manage.py reset-db      # wipe ALL data (keeps rules/keywords)
"""

import os, sys, signal, subprocess, time, webbrowser

BASE   = os.path.dirname(os.path.abspath(__file__))
PID    = os.path.join(BASE, '.pid')
LOG    = os.path.join(BASE, 'logs', 'app.log')
APP    = os.path.join(BASE, 'app.py')
HOST   = 'rupeexpenses'
PORT   = 5050
URL    = f'http://{HOST}:{PORT}'


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_pid():
    try:
        return int(open(PID).read().strip())
    except Exception:
        return None


def is_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def print_ok(msg):  print(f'\033[32m✓\033[0m  {msg}')
def print_err(msg): print(f'\033[31m✗\033[0m  {msg}')
def print_info(msg):print(f'\033[34m→\033[0m  {msg}')


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_start():
    pid = read_pid()
    if is_running(pid):
        print_info(f'Already running  (PID {pid})  →  {URL}')
        return

    os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
    log_fd = open(LOG, 'a')

    proc = subprocess.Popen(
        [sys.executable, APP],
        stdout=log_fd, stderr=log_fd,
        cwd=BASE,
        env={**os.environ, 'EXPENSES_DEBUG': '0'},
    )
    open(PID, 'w').write(str(proc.pid))

    # Wait up to 3 s for the server to bind
    for _ in range(15):
        time.sleep(0.2)
        if not is_running(proc.pid):
            break
        try:
            import urllib.request
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/', timeout=1)
            break
        except Exception:
            pass

    if is_running(proc.pid):
        print_ok(f'Started  (PID {proc.pid})  →  {URL}')
        print_info(f'Logs: {LOG}')
    else:
        print_err(f'Failed to start — check {LOG}')


def cmd_stop():
    pid = read_pid()
    if not is_running(pid):
        print_info('Not running')
        if os.path.exists(PID):
            os.remove(PID)
        return

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        time.sleep(0.25)
        if not is_running(pid):
            break

    if is_running(pid):
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)

    if os.path.exists(PID):
        os.remove(PID)
    print_ok(f'Stopped  (was PID {pid})')


def cmd_restart():
    cmd_stop()
    time.sleep(0.5)
    cmd_start()


def cmd_status():
    pid = read_pid()
    if is_running(pid):
        print_ok(f'Running  (PID {pid})  →  {URL}')
    else:
        print_err('Stopped')
        if pid:
            print_info(f'Stale PID file removed')
            os.remove(PID)


def cmd_open():
    pid = read_pid()
    if not is_running(pid):
        print_info('Not running — starting first…')
        cmd_start()
        time.sleep(1)
    webbrowser.open(URL)
    print_ok(f'Opened  {URL}')


def cmd_logs():
    if not os.path.exists(LOG):
        print_info('No log file yet — start the app first')
        return
    print_info(f'Tailing {LOG}  (Ctrl-C to stop)\n')
    try:
        subprocess.run(['tail', '-f', '-n', '60', LOG])
    except KeyboardInterrupt:
        pass


def cmd_reset_db():
    answer = input(
        '\033[31mThis will DELETE all transactions and accounts.\033[0m\n'
        'Category rules and wasted keywords are kept.\n'
        'Type YES to confirm: '
    ).strip()
    if answer != 'YES':
        print_info('Cancelled')
        return

    import sqlite3
    DB = os.path.join(BASE, 'data', 'expenses.db')
    conn = sqlite3.connect(DB)
    conn.execute('DELETE FROM transactions')
    conn.execute('DELETE FROM accounts')
    conn.commit()
    conn.close()
    print_ok('All transactions and accounts deleted. Rules kept.')


# ── Dispatch ──────────────────────────────────────────────────────────────────

COMMANDS = {
    'start':    cmd_start,
    'stop':     cmd_stop,
    'restart':  cmd_restart,
    'status':   cmd_status,
    'open':     cmd_open,
    'logs':     cmd_logs,
    'reset-db': cmd_reset_db,
}

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd not in COMMANDS:
        print(f'Unknown command: {cmd}')
        print('Usage: python3 manage.py [' + ' | '.join(COMMANDS) + ']')
        sys.exit(1)
    COMMANDS[cmd]()
