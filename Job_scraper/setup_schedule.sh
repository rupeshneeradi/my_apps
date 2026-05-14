#!/bin/bash
# setup_schedule.sh — v1.0.0
# Installs macOS launchd jobs for the Job Pipeline:
#   • Portal Pipeline  : Mon–Fri at 06:45 AM
#   • Vendor Pipeline  : Mon & Thu at 06:50 AM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(which python3)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

echo "=== Job Pipeline Scheduler Setup v1.0.0 ==="
echo "Script dir : $SCRIPT_DIR"
echo "Python     : $PYTHON"
echo "LaunchAgents: $LAUNCH_DIR"
echo ""

mkdir -p "$LAUNCH_DIR"

# ── 1. Portal Pipeline — Mon-Fri 06:45 AM ────────────────────────────────────
PORTAL_PLIST="$LAUNCH_DIR/com.jobpipeline.portals.plist"
cat > "$PORTAL_PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobpipeline.portals</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/run_portals.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>StartCalendarInterval</key>
    <array>
        <!-- Monday 06:45 -->
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>45</integer></dict>
        <!-- Tuesday 06:45 -->
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>45</integer></dict>
        <!-- Wednesday 06:45 -->
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>45</integer></dict>
        <!-- Thursday 06:45 -->
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>45</integer></dict>
        <!-- Friday 06:45 -->
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>45</integer></dict>
    </array>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/portal_launchd.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/portal_launchd_err.log</string>

    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST

# ── 2. Vendor Pipeline — Mon & Thu 06:50 AM ───────────────────────────────────
VENDOR_PLIST="$LAUNCH_DIR/com.jobpipeline.vendors.plist"
cat > "$VENDOR_PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobpipeline.vendors</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/run_vendors.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>StartCalendarInterval</key>
    <array>
        <!-- Monday 06:50 -->
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>50</integer></dict>
        <!-- Thursday 06:50 -->
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>50</integer></dict>
    </array>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/logs/vendor_launchd.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/logs/vendor_launchd_err.log</string>

    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLIST

# ── Load both agents ──────────────────────────────────────────────────────────
echo "Loading launchd agents..."

launchctl unload "$PORTAL_PLIST" 2>/dev/null || true
launchctl load   "$PORTAL_PLIST"
echo "✅ Portal Pipeline loaded: Mon-Fri 06:45 AM"

launchctl unload "$VENDOR_PLIST" 2>/dev/null || true
launchctl load   "$VENDOR_PLIST"
echo "✅ Vendor Pipeline loaded: Mon & Thu 06:50 AM"

echo ""
echo "=== Schedule active. Verify with: ==="
echo "  launchctl list | grep jobpipeline"
echo ""
echo "=== To uninstall: ==="
echo "  launchctl unload ~/Library/LaunchAgents/com.jobpipeline.portals.plist"
echo "  launchctl unload ~/Library/LaunchAgents/com.jobpipeline.vendors.plist"
echo ""
echo "=== To run NOW (test): ==="
echo "  cd $SCRIPT_DIR && python3 run_portals.py"
echo "  cd $SCRIPT_DIR && python3 run_vendors.py"
