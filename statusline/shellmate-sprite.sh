#!/usr/bin/env bash
# shellmate statusline sprite — animated companion above the info line.
#
# Runs once per statusline render in EVERY Claude pane. With refreshInterval=1
# and ~10 panes that is ~10 invocations/second, forever. So the hot path here is
# pure bash — no Python, no subprocesses:
#
#   cold path (every $TTL seconds, backgrounded): poll sessions, render both
#                                                 animation frames, cache them
#   hot path  (every render):                     cat one cached frame
#
# Display-only: never notifies. Fails silent, so the statusline degrades to its
# normal single line if anything breaks.

SHELLMATE_HOME="${SHELLMATE_HOME:=$(cd "$(dirname "$0")/.." && pwd)}"
CACHE_ROOT="${XDG_RUNTIME_DIR:-/tmp}/shellmate"
TTL=2
STALENESS_THRESHOLD=$((TTL * 6))  # 12 seconds

[ -d "$SHELLMATE_HOME" ] || exit 0

# Portable mtime helper: works on both GNU and BSD/macOS
# GNU: stat -c %Y, BSD/macOS: stat -f %m, fallback: echo 0
file_mtime() {
    stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

# Portable bounded-run helper. `timeout` is GNU coreutils and does NOT exist on
# macOS; Homebrew's coreutils installs it as `gtimeout`. Without this shim the
# cold path dies on every Mac, no frames are ever cached, and the buddy never
# appears at all. Running unbounded is an acceptable last resort: the cold path
# is already backgrounded, so a hung one costs nothing the user can see.
run_bounded() {
    _secs="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$_secs" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$_secs" "$@"
    else
        "$@"
    fi
}

# Determine cache directory based on session ID
# Sanitize session_id to prevent path traversal (only alphanumeric, -, _)
if [ -n "$SHELLMATE_SESSION_ID" ]; then
    sanitized=$(printf "%s" "$SHELLMATE_SESSION_ID" | tr -cd 'A-Za-z0-9_-')
    CACHE_DIR="$CACHE_ROOT/$sanitized"
else
    # Fall back to aggregate cache
    CACHE_DIR="$CACHE_ROOT/aggregate"
fi

mkdir -p "$CACHE_DIR" 2>/dev/null || exit 0

stamp="$CACHE_DIR/stamp"
now=$(date +%s)
stale=1
if [ -f "$stamp" ]; then
    mtime=$(file_mtime "$stamp")
    [ $((now - mtime)) -lt "$TTL" ] && stale=0
fi

# --- cold path: refresh the cached frames in the background, never blocking ---
if [ "$stale" -eq 1 ]; then
    : > "$stamp"          # claim the refresh immediately so panes do not stampede
    (
        cd "$SHELLMATE_HOME" || exit 0
        # Clean up old per-session caches (not touched in over 1 hour)
        if [ -n "$SHELLMATE_SESSION_ID" ]; then
            find "$CACHE_ROOT" -maxdepth 1 -type d -name "[A-Za-z0-9_-]*" -mmin +60 -exec rm -rf {} + 2>/dev/null || true
        fi
        CACHE_DIR="$CACHE_DIR" run_bounded 3 python3 - <<'PY' 2>/dev/null
import os, time
from shellmate import __version__
from shellmate.characters import frames_for, hatch_stage, idle_frame, EGG, stage_for, apply_petting, phrase_for, egg_phrase_for
from shellmate.config import load_config
from shellmate.escalation import advance
from shellmate.session import sample
from shellmate.store import default_path, identity_path, load, load_identity, save_identity, save
from shellmate.theme import COLORS, RESET
from shellmate.textwidth import width, truncate
from shellmate.identity import new_seed, name_from_seed, species_from_seed, Identity
from shellmate.update import check_for_update_cached

cache = os.environ["CACHE_DIR"]
session_id = os.environ.get("SHELLMATE_SESSION_ID", "")
cfg = load_config()
st = load(default_path())
now_time = time.time()

# Initialize or load identity (from separate identity.json file)
identity = load_identity(identity_path())
if identity is None:
    seed = new_seed()
    identity = Identity(
        seed=seed,
        name=name_from_seed(seed),
        species=species_from_seed(seed),
        born_at=now_time,
    )
    save_identity(identity_path(), identity)

sessions, online = sample()

# Check for updates if enabled (cold path only; never blocks hot path)
latest_version = None
if online:
    latest_version = check_for_update_cached(__version__, now_time, enabled=cfg.check_updates)

snap, st, _ = advance(sessions, st, now_time, cfg, online, latest_version=latest_version)  # alerts discarded: display-only
save(default_path(), st)

# Determine which character to display
effective_character = cfg.character if cfg.character else identity.species

# Use per-session mood if session_id is available, otherwise use aggregate
if session_id:
    from shellmate.escalation import mood_for_session
    mood = mood_for_session(snap, session_id)
else:
    mood = snap.mood

# Apply petting effect to mood (unless alert/alarmed/offline)
mood = apply_petting(mood, st.petted_at, now_time)

role = {"sleeping": "dim", "working": "blue", "happy": "green", "perked": "green",
        "alert": "yellow", "alarmed": "red", "offline": "dim"}[mood]
col, reset = COLORS[role], RESET

# Check if we're still hatching (duration defaults to EGG_SECONDS = 8 hours)
egg_idx = hatch_stage(identity.born_at, now_time)

if egg_idx is not None:
    # Render egg frames during hatching
    frames_data = EGG
else:
    # Determine stage and use appropriate sprites
    buddy_stage = stage_for(identity.born_at, now_time)
    frames_data = frames_for(effective_character, mood, stage=buddy_stage)

# Render frames for current mood
for i in range(2):
    frame = frames_data[i % len(frames_data)]
    body = "\n".join(f"{col}{ln}{reset}" for ln in frame)

    # Append name and phrase if configured
    body_lines = body.split("\n")
    if body_lines:
        last_line = body_lines[-1]

        if egg_idx is not None:
            # Egg stage: append egg phrase if configured
            # Seed from born_at (stable for the egg's lifetime) not mood_since (which churns)
            egg_phrase_display = ""
            if cfg.show_phrase:
                egg_phrase_text = egg_phrase_for(egg_idx, identity.born_at)
                if egg_phrase_text:
                    egg_phrase_display = f"  {COLORS['dim']}\"{egg_phrase_text}\"{reset}"
            combined = last_line + egg_phrase_display
        else:
            # Mood stage: append name and phrase if configured
            name_display = ""
            if cfg.show_name:
                name_display = f"  {COLORS['dim']}{identity.name}{reset}"

            phrase_display = ""
            if cfg.show_phrase:
                phrase_text = st.phrase_text
                if phrase_text:
                    phrase_display = f"  {COLORS['dim']}\"{phrase_text}\"{reset}"

            combined = last_line + name_display + phrase_display

        body_lines[-1] = combined
        body = "\n".join(body_lines)

    tmp = f"{cache}/frame{i}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    os.replace(tmp, f"{cache}/frame{i}")

# Also render an offline frame for use when staleness is detected
offline_frames = frames_for(effective_character, "offline")
offline_col, offline_reset = COLORS["dim"], RESET
for i in range(2):
    frame = offline_frames[i % len(offline_frames)]
    body = "\n".join(f"{offline_col}{ln}{offline_reset}" for ln in frame)
    if egg_idx is None:
        body_lines = body.split("\n")
        if body_lines:
            last_line = body_lines[-1]

            # Append name if configured
            name_display = ""
            if cfg.show_name:
                name_display = f"  {COLORS['dim']}{identity.name}{offline_reset}"

            # Append phrase if configured (offline phrase)
            phrase_display = ""
            if cfg.show_phrase:
                phrase_text = st.phrase_text
                if phrase_text:
                    phrase_display = f"  {COLORS['dim']}\"{phrase_text}\"{offline_reset}"

            # Combine
            combined = last_line + name_display + phrase_display
            body_lines[-1] = combined
            body = "\n".join(body_lines)
    tmp = f"{cache}/offline.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    os.replace(tmp, f"{cache}/offline")
PY
    ) >/dev/null 2>&1 &
fi

# --- hot path: pure bash, just print the frame for this second ---
frame=$(( now % 2 ))

# Check for staleness: if frame is older than STALENESS_THRESHOLD, render offline instead
frame_file="$CACHE_DIR/frame$frame"
if [ -f "$frame_file" ]; then
    frame_mtime=$(file_mtime "$frame_file")
    age=$((now - frame_mtime))
    if [ "$age" -gt "$STALENESS_THRESHOLD" ]; then
        # Cache is stale; render offline face if available
        [ -f "$CACHE_DIR/offline" ] && cat "$CACHE_DIR/offline"
    else
        cat "$frame_file"
    fi
fi
exit 0
