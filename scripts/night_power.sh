#!/bin/zsh
# Atlas night power schedule (Mac side).
# The projector app handles: boot-on (HOME app), bedtime watcher, backlight-off,
# and wake-on-cry. This script only performs the hard power-off at dawn and is
# optional — the projector is fully usable without it.
#
# Install (one-time):
#   sudo launchctl atlas-night-power: add a LaunchAgent plist or cron entry:
#   crontab -e  →  45 6 * * * /path/to/atlas-projector/scripts/night_power.sh

ADB="$HOME/Library/Android/sdk/platform-tools/adb"
TARGET="192.168.86.72:5555"

$ADB connect "$TARGET" >/dev/null 2>&1
sleep 2
if $ADB -s "$TARGET" get-state 2>/dev/null | grep -q device; then
  echo "$(date) powering off $TARGET"
  $ADB -s "$TARGET" shell reboot -p
else
  echo "$(date) projector not reachable; skipping power-off"
fi
