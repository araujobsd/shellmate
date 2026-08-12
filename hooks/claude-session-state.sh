#!/bin/sh
# Claude Code hook for tracking session state.
#
# Called by Claude Code on hook events. Reads hook JSON from stdin and writes
# session state to ${XDG_STATE_HOME:-$HOME/.local/state}/shellmate/sessions/<session_id>.json
#
# This script must be defensive: if python3 is missing, JSON is unparseable, or
# the state dir cannot be created, it exits 0 silently. A hook that errors
# pollutes the user's Claude session.

set -e

# Helper: parse JSON from stdin using python3
# On error or missing python3, returns empty string
parse_json() {
    key="$1"
    python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('$key', ''))
except:
    pass
" 2>/dev/null || printf ""
}

# Read hook JSON from stdin into a temp file
hook_json=$(mktemp)
trap "rm -f '$hook_json'" EXIT

if ! cat > "$hook_json"; then
    exit 0
fi

# Parse required fields
event=$(parse_json "hook_event_name" < "$hook_json")
session_id=$(parse_json "session_id" < "$hook_json")
cwd=$(parse_json "cwd" < "$hook_json")

# Must have at least event and session_id
if [ -z "$event" ] || [ -z "$session_id" ]; then
    exit 0
fi

# Ignore SubagentStop entirely — it can revive finished sessions
if [ "$event" = "SubagentStop" ]; then
    exit 0
fi

# Determine state directory
state_base="${XDG_STATE_HOME:-$HOME/.local/state}"
state_dir="$state_base/shellmate/sessions"

# Try to create state directory
if ! mkdir -p "$state_dir" 2>/dev/null; then
    exit 0
fi

session_file="$state_dir/$session_id.json"

# Map event to status
status=""
case "$event" in
    UserPromptSubmit | SessionStart)
        status="working"
        ;;
    Stop)
        status="done"
        ;;
    SessionEnd)
        # Delete the session file on end
        rm -f "$session_file" 2>/dev/null
        exit 0
        ;;
    *)
        # Ignore unknown events
        exit 0
        ;;
esac

if [ -z "$status" ]; then
    exit 0
fi

# Write session state file using python3 for JSON encoding
python3 -c "
import json, sys, time, os

try:
    state = {
        'session_id': '$session_id',
        'status': '$status',
        'cwd': '$cwd',
        'ts': int(time.time())
    }
    with open('$session_file', 'w') as f:
        json.dump(state, f)
except:
    pass
" 2>/dev/null

exit 0
