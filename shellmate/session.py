"""Claude Code session source: agent data from hook-written session files."""

import contextlib
import json
import os
import time
from pathlib import Path

from shellmate.models import Agent

# Sessions older than this many seconds are considered stale and ignored
STALE_SECONDS = 8 * 3600  # 8 hours


def sample() -> tuple[list[Agent], bool]:
    """Return (agents, online) by reading session files.

    Reads all *.json files in the sessions directory, converting each to an Agent.
    Stale session files (older than STALE_SECONDS) are ignored and deleted.
    Returns (agents, True) — a missing directory or empty directory is not offline.
    """
    sessions_dir = _sessions_dir()
    agents = []
    now = time.time()

    if not sessions_dir.exists():
        return [], True

    try:
        for session_file in sessions_dir.glob("*.json"):
            # Check staleness
            mtime = session_file.stat().st_mtime
            if now - mtime > STALE_SECONDS:
                # Clean up stale file
                with contextlib.suppress(OSError):
                    session_file.unlink()
                continue

            # Parse session file
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                # Skip malformed files
                continue

            if not isinstance(data, dict):
                continue

            session_id = data.get("session_id", "")
            status = data.get("status", "unknown")
            cwd = data.get("cwd", "")

            if not session_id:
                continue

            # Extract label from cwd basename
            label = cwd.rsplit("/", 1)[-1] if cwd else session_id

            agents.append(
                Agent(
                    key=session_id,
                    status=status,
                    label=label,
                    pane_id="",  # No panes in Claude session source
                    tab_id="",
                )
            )
    except OSError:
        # If we can't read the directory, still return success (offline means source broken)
        pass

    return agents, True


def _sessions_dir() -> Path:
    """Return the sessions directory path."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shellmate" / "sessions"
