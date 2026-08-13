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
# The one exception is a cold cache, where the cold path runs in the FOREGROUND:
# there is no cached frame to print, and blocking once (~250ms measured) beats
# rendering an empty status line that grows by three lines a second later.
#
# Display-only: never notifies. Fails silent, so the statusline degrades to its
# normal single line if anything breaks.

SHELLMATE_HOME="${SHELLMATE_HOME:=$(cd "$(dirname "$0")/.." && pwd)}"
CACHE_ROOT="${XDG_RUNTIME_DIR:-/tmp}/shellmate"
TTL=2
STALENESS_THRESHOLD=$((TTL * 6))  # 12 seconds
WARMUP_COOLDOWN=300               # after a failed foreground warmup, don't retry for 5 min

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

# --- cold path: re-render both frames. Backgrounded normally; run in the
# foreground on a cold cache, see the dispatch below. ---
render_cold() {
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
from shellmate.theme import COLORS, RESET, species_color, split_marks
from shellmate.textwidth import width, truncate
from shellmate.identity import new_seed, name_from_seed, species_from_seed, Identity
from shellmate.update import check_for_update_cached

cache = os.environ["CACHE_DIR"]
session_id = os.environ.get("SHELLMATE_SESSION_ID", "")


def session_phrase(state, sid):
    """Read this pane's phrase, falling back to the shared slot.

    Panes all share one state.json, so each has its own phrase slot; the shared
    field belongs to the aggregate surfaces (--face, the full-screen app).
    """
    if sid:
        return state.phrase_by_session.get(sid, "")
    return state.phrase_text

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

# session_id makes advance() pick the phrase for THIS pane's mood and keep it in
# this pane's own slot. Without it the phrase came from the aggregate mood across
# every pane, so a quiet pane quoted whichever other pane was worst off.
snap, st, _ = advance(sessions, st, now_time, cfg, online, latest_version=latest_version, session_id=session_id)  # alerts discarded: display-only
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


def paint(line, body_col, mark_col):
    """Body in the species colour, trailing marks in the mood colour."""
    body_part, marks = split_marks(line)
    out = f"{body_col}{body_part}{RESET}"
    if marks:
        out += f"{mark_col}{marks}{RESET}"
    return out

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
    # The egg has no species yet, so it stays on the mood colour; once hatched the
    # body wears the species colour and only the marks track the mood.
    frame_body_col = col if egg_idx is not None else species_color(effective_character)
    body = "\n".join(paint(ln, frame_body_col, col) for ln in frame)

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
                # Name carries the mood colour: it is the urgency channel now that
                # the body is a fixed species colour.
                name_display = f"  {col}{identity.name}{reset}"

            phrase_display = ""
            if cfg.show_phrase:
                phrase_text = session_phrase(st, session_id)
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
    body = "\n".join(paint(ln, species_color(effective_character), offline_col) for ln in frame)
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
                phrase_text = session_phrase(st, session_id)
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
    )
}

# Both call sites MUST redirect here rather than inside render_cold. Backgrounding
# a function call forks a shell that holds the caller's stdout — our status line's
# command-substitution pipe — open for the whole render, so `$(...)` blocks until
# the "background" work finishes. Redirecting at the call site closes that pipe
# before the render starts. Measured: 20ms with, 230ms without.

# A cold cache has no frames for the hot path to print, so the first render of a
# new session printed nothing at all and the status line grew by three lines a
# second later. Render in the foreground just that once (~110ms) so the buddy is
# there from the very first frame.
cold=0
{ [ -f "$CACHE_DIR/frame0" ] && [ -f "$CACHE_DIR/frame1" ]; } || cold=1

# Blocking is only acceptable because it happens once. On an install where the
# render cannot work at all — no python3, broken import — every render would
# otherwise stall for the full run_bounded timeout, which is far worse than the
# empty frame this fixes. So one failed warmup disables foreground rendering for
# WARMUP_COOLDOWN and we fall back to the old behaviour: background, empty first.
warmup=0
if [ "$cold" -eq 1 ] && command -v python3 >/dev/null 2>&1; then
    warmup=1
    marker="$CACHE_ROOT/warmup_failed"
    if [ -f "$marker" ] && [ $((now - $(file_mtime "$marker"))) -lt "$WARMUP_COOLDOWN" ]; then
        warmup=0
    fi
fi

if [ "$stale" -eq 1 ]; then
    : > "$stamp"          # claim the refresh immediately so panes do not stampede
    if [ "$warmup" -eq 1 ]; then
        render_cold >/dev/null 2>&1
        # Frames still missing means the render is broken, not merely slow.
        [ -f "$CACHE_DIR/frame0" ] || : > "$CACHE_ROOT/warmup_failed"
    else
        render_cold >/dev/null 2>&1 &
    fi
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
