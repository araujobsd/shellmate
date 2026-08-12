#!/bin/sh
# Install shellmate into Claude Code configuration.
#
# This script:
#   1. Verifies python3 >= 3.11
#   2. Installs the session hook
#   3. Sets refreshInterval = 1
#   4. Wires the sprite script into the status line (preserving existing commands)
#   5. Backs up ~/.claude/settings.json before modification
#   6. Is idempotent and supports --uninstall
#
# Usage:
#   ./install.sh           # Install
#   ./install.sh --uninstall  # Uninstall (restores from backup)

set -e

UNINSTALL=0
if [ "$1" = "--uninstall" ]; then
    UNINSTALL=1
fi

# Detect the repository root (parent of this script's directory)
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SPRITE_SCRIPT="$REPO_DIR/statusline/shellmate-sprite.sh"
HOOK_SCRIPT="$REPO_DIR/hooks/claude-session-state.sh"
CLAUDE_CONFIG_DIR="$HOME/.claude"
SETTINGS_JSON="$CLAUDE_CONFIG_DIR/settings.json"
BACKUP_SUFFIX="_backup_$(date +%s)"

# --- Utility functions ---

die() {
    printf "shellmate install: %s\n" "$1" >&2
    exit 1
}

validate_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        die "python3 not found. Please install Python 3.11 or later."
    fi

    version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    case "$version" in
        3.11 | 3.12 | 3.13 | 3.14 | 4.*) ;;
        *)
            die "python3 version $version found, but 3.11+ required"
            ;;
    esac
}

ensure_settings_json() {
    if [ ! -f "$SETTINGS_JSON" ]; then
        mkdir -p "$CLAUDE_CONFIG_DIR" 2>/dev/null || die "Cannot create $CLAUDE_CONFIG_DIR"
        cat > "$SETTINGS_JSON" <<'EOF'
{
  "hooks": {},
  "statusLine": {
    "refreshInterval": 1
  }
}
EOF
    fi
}

backup_settings() {
    cp "$SETTINGS_JSON" "$SETTINGS_JSON$BACKUP_SUFFIX"
    printf "Backed up to: %s\n" "$SETTINGS_JSON$BACKUP_SUFFIX"
}

# Extract/set a value in JSON using python3
# Usage: json_set <file> <key_path> <value> [type]
# key_path: "toplevel.nested.key" for {toplevel: {nested: {key: value}}}
# type: "string" (default), "number", "bool", or "json" for raw JSON
json_set() {
    file="$1"
    key_path="$2"
    value="$3"
    type="${4:-string}"

    python3 - "$file" "$key_path" "$value" "$type" <<'PYEOF'
import json, sys, os

file = sys.argv[1]
key_path = sys.argv[2]
value = sys.argv[3]
value_type = sys.argv[4]

# Read or create
if os.path.exists(file):
    with open(file) as f:
        data = json.load(f)
else:
    data = {}

# Parse the path
keys = key_path.split(".")
node = data
for key in keys[:-1]:
    if key not in node:
        node[key] = {}
    node = node[key]

# Convert value to correct type
if value_type == "json":
    final_value = json.loads(value)
elif value_type == "bool":
    final_value = value.lower() in ("true", "1", "yes")
elif value_type == "number":
    final_value = float(value) if "." in value else int(value)
else:  # string
    final_value = value

# Set value
node[keys[-1]] = final_value

# Write back
with open(file, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

# Check if a hook is already installed
hook_exists() {
    hook_name="$1"
    python3 - "$SETTINGS_JSON" "$hook_name" <<'PYEOF'
import json, sys
settings_file = sys.argv[1]
hook_name = sys.argv[2]

try:
    with open(settings_file) as f:
        data = json.load(f)
    hooks = data.get("hooks", {})
    sys.exit(0 if hook_name in hooks else 1)
except:
    sys.exit(1)
PYEOF
}

# Check if a hook has a specific handler
hook_has_handler() {
    hook_name="$1"
    handler="$2"
    python3 - "$SETTINGS_JSON" "$hook_name" "$handler" <<'PYEOF'
import json, sys
settings_file = sys.argv[1]
hook_name = sys.argv[2]
handler = sys.argv[3]

try:
    with open(settings_file) as f:
        data = json.load(f)
    hooks = data.get("hooks", {})
    hook_handlers = hooks.get(hook_name, [])
    if isinstance(hook_handlers, str):
        hook_handlers = [hook_handlers]
    sys.exit(0 if handler in hook_handlers else 1)
except:
    sys.exit(1)
PYEOF
}

# Add a handler to a hook (idempotent)
hook_add_handler() {
    hook_name="$1"
    handler="$2"

    if hook_has_handler "$hook_name" "$handler"; then
        return 0  # Already there
    fi

    python3 - "$SETTINGS_JSON" "$hook_name" "$handler" <<'PYEOF'
import json, sys
settings_file = sys.argv[1]
hook_name = sys.argv[2]
handler = sys.argv[3]

with open(settings_file) as f:
    data = json.load(f)

if "hooks" not in data:
    data["hooks"] = {}

hook_list = data["hooks"].get(hook_name, [])
if isinstance(hook_list, str):
    hook_list = [hook_list]
elif not isinstance(hook_list, list):
    hook_list = []

if handler not in hook_list:
    hook_list.append(handler)

data["hooks"][hook_name] = hook_list

with open(settings_file, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

# Remove a handler from a hook
hook_remove_handler() {
    hook_name="$1"
    handler="$2"

    python3 - "$SETTINGS_JSON" "$hook_name" "$handler" <<'PYEOF'
import json, sys
settings_file = sys.argv[1]
hook_name = sys.argv[2]
handler = sys.argv[3]

with open(settings_file) as f:
    data = json.load(f)

if "hooks" in data and hook_name in data["hooks"]:
    hook_list = data["hooks"][hook_name]
    if isinstance(hook_list, str):
        hook_list = [hook_list]
    if handler in hook_list:
        hook_list.remove(handler)
    data["hooks"][hook_name] = hook_list if hook_list else []

with open(settings_file, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

# Check if a value is set in settings.json
json_has_value() {
    key_path="$1"
    expected="$2"

    python3 - "$SETTINGS_JSON" "$key_path" "$expected" <<'PYEOF'
import json, sys

settings_file = sys.argv[1]
key_path = sys.argv[2]
expected = sys.argv[3]

try:
    with open(settings_file) as f:
        data = json.load(f)

    keys = key_path.split(".")
    node = data
    for key in keys:
        if key not in node:
            sys.exit(1)
        node = node[key]

    # Handle different types
    if isinstance(node, bool):
        sys.exit(0 if str(node).lower() == expected.lower() else 1)
    elif isinstance(node, (int, float)):
        sys.exit(0 if str(node) == expected else 1)
    else:
        sys.exit(0 if str(node) == expected else 1)
except:
    sys.exit(1)
PYEOF
}

# --- Uninstall ---
if [ "$UNINSTALL" = 1 ]; then
    ensure_settings_json

    printf "Removing shellmate configuration...\n"

    # Surgically remove only what we added, preserving other user settings
    hook_remove_handler "UserPromptSubmit" "$HOOK_SCRIPT"
    hook_remove_handler "Stop" "$HOOK_SCRIPT"
    hook_remove_handler "SessionStart" "$HOOK_SCRIPT"
    hook_remove_handler "SessionEnd" "$HOOK_SCRIPT"

    # Note: we do NOT remove statusLine.command because the user may have manually
    # integrated shellmate there, and we cannot safely distinguish our code from theirs.
    # They should manually remove the shellmate lines from their status line script.

    printf "Uninstall complete.\n"
    printf "Note: if you manually added shellmate to your status line script,\n"
    printf "      please remove those lines from %s\n" "$HOME/.claude/hooks/*"
    exit 0
fi

# --- Install ---
printf "Installing shellmate into Claude Code...\n"

validate_python

ensure_settings_json
backup_settings

# Install hooks
printf "Installing session hooks...\n"
hook_add_handler "UserPromptSubmit" "$HOOK_SCRIPT"
hook_add_handler "Stop" "$HOOK_SCRIPT"
hook_add_handler "SessionStart" "$HOOK_SCRIPT"
hook_add_handler "SessionEnd" "$HOOK_SCRIPT"

# Set refreshInterval = 1
printf "Setting statusLine.refreshInterval to 1...\n"
json_set "$SETTINGS_JSON" "statusLine.refreshInterval" "1" "number"

# Handle status line sprite setup
printf "Configuring status line sprite...\n"

# Check if statusLine.command already exists
status_line_cmd=$(python3 - "$SETTINGS_JSON" <<'PYEOF'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    cmd = data.get("statusLine", {}).get("command", "")
    print(cmd)
except:
    print("")
PYEOF
)

if [ -n "$status_line_cmd" ] && [ "$status_line_cmd" != "null" ]; then
    printf "\n"
    printf "You have an existing statusLine.command. To integrate shellmate:\n"
    printf "\n"
    printf "The sprite is a multi-line output that must render ABOVE your status line.\n"
    printf "In your status line script, before the final printf/echo, capture the sprite\n"
    printf "and emit it first. Here is the pattern:\n"
    printf "\n"
    printf "  # Extract session_id from stdin JSON\n"
    printf "  session_id=\$(printf '%%s' \"\$input\" | python3 -c \"import sys, json; print(json.load(sys.stdin).get('session_id', ''))\" 2>/dev/null)\n"
    printf "  # Or without jq/python, using grep:\n"
    printf "  # session_id=\$(printf '%%s' \"\$input\" | grep -o '\"session_id\":\"[^\"]*\"' | cut -d'\"' -f4)\n"
    printf "\n"
    printf "  sprite=\$(SHELLMATE_HOME='%s' SHELLMATE_SESSION_ID=\"\$session_id\" bash '%s' 2>/dev/null)\n" "$REPO_DIR" "$SPRITE_SCRIPT"
    printf "  if [ -n \"\$sprite\" ]; then\n"
    printf "    printf '%%s\\\\n%%s' \"\$sprite\" \"\$your_status_content\"\n"
    printf "  else\n"
    printf "    printf '%%s' \"\$your_status_content\"\n"
    printf "  fi\n"
    printf "\n"
    printf "This ensures: (1) the sprite appears first (above the status line),\n"
    printf "(2) your status content appears below, (3) each pane shows its own buddy mood,\n"
    printf "(4) the status line still renders normally if the buddy fails to load.\n"
    printf "\n"
    printf "If you omit SHELLMATE_SESSION_ID, the buddy shows the aggregate mood across\n"
    printf "all sessions instead (backward compatible with older Claude Code versions).\n"
    printf "\n"
else
    # No existing command, install the sprite script directly
    printf "Creating status line command...\n"
    # The status line will receive session_id in its stdin JSON; extract it and pass to sprite
    sprite_cmd="session_id=\$(printf '%s' \"\$input\" | python3 -c \"import sys, json; print(json.load(sys.stdin).get('session_id', ''))\" 2>/dev/null); SHELLMATE_HOME='$REPO_DIR' SHELLMATE_SESSION_ID=\"\$session_id\" bash '$SPRITE_SCRIPT'"
    json_set "$SETTINGS_JSON" "statusLine.command" "$sprite_cmd" "string"
fi

printf "\n"
printf "Installation complete.\n"
printf "Settings backed up to: %s\n" "$SETTINGS_JSON$BACKUP_SUFFIX"
printf "\n"
printf "Next: reload Claude Code and your buddy will appear in the status line.\n"
