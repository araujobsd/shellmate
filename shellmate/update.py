"""Check for new releases on GitHub.

Pure apart from the injected `fetch` function, so it is testable without network.
"""

import json
import urllib.request
from pathlib import Path

UPDATE_CHECK_INTERVAL = 86400  # 24 hours


def _parse_version(version_str: str | None) -> tuple[int, ...] | None:
    """Parse a version string like '0.10.0' or 'v0.10.0' into a tuple of ints.

    Returns None if the version cannot be parsed.
    Pure function.
    """
    if version_str is None or not isinstance(version_str, str):
        return None

    # Strip leading 'v' if present
    version_str = version_str.lstrip("v")

    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return None


def check_for_update(current: str, fetch=None) -> str | None:
    """Check if a newer version is available on GitHub.

    Args:
        current: current version string like "0.1.0"
        fetch: optional function(url, timeout) -> dict, defaulting to urllib

    Returns:
        Newer version string (without 'v' prefix) if available, None otherwise.

    Pure apart from the injected `fetch`, so it is testable without network.
    """
    if fetch is None:

        def fetch(url: str, timeout: int) -> dict:
            req = urllib.request.Request(url, headers={"User-Agent": "shellmate/0.1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))

    try:
        data = fetch("https://api.github.com/repos/araujobsd/shellmate/releases/latest", 5)
    except (OSError, ValueError, KeyError, TypeError):
        # Network failure, timeout, rate limit, 403/404 (no releases published),
        # malformed JSON, unexpected shape: all silent. Deliberately NOT a bare
        # `except Exception` — that also swallows programming errors, which would
        # disable update checking permanently with no signal that anything broke.
        return None

    if not data or "tag_name" not in data:
        return None

    tag_name = data.get("tag_name", "")
    latest = _parse_version(tag_name)
    current_parsed = _parse_version(current)

    if latest is None or current_parsed is None:
        return None

    # Compare as tuples (e.g., (0, 10, 0) > (0, 9, 0))
    if latest > current_parsed:
        # Return without the 'v' prefix
        return tag_name.lstrip("v")

    return None


def get_cache_path() -> Path:
    """Get the cache file path for update status.

    Returns ~/.local/state/shellmate/update.json by default.
    Pure function.
    """
    base = Path.home() / ".local" / "state" / "shellmate"
    base.mkdir(parents=True, exist_ok=True)
    return base / "update.json"


def load_cached_check() -> dict | None:
    """Load cached update check result.

    Returns dict with keys 'checked_at' (unix timestamp) and 'latest' (version or None).
    Returns None if cache is missing or corrupt.
    """
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.loads(f.read())
    except (OSError, json.JSONDecodeError):
        # Corrupt or unreadable: treat as unchecked, never raise
        return None


def save_cached_check(latest_version: str | None, checked_at: float) -> None:
    """Save update check result to cache.

    Args:
        latest_version: version string if available, None otherwise
        checked_at: unix timestamp of the check
    """
    cache_path = get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"checked_at": int(checked_at), "latest": latest_version}
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data))
    except OSError:
        # Silently ignore cache write failures
        pass


def check_for_update_cached(
    current: str, now: float, fetch=None, enabled: bool = True
) -> str | None:
    """Check for updates, using cache to avoid frequent network calls.

    Args:
        current: current version string like "0.1.0"
        now: current unix timestamp
        fetch: optional function(url, timeout) -> dict for testing
        enabled: if False, never make a network call and return cached result only

    Returns:
        Newer version string if available, None otherwise.
    """
    cached = load_cached_check()

    # Check if cache is still fresh
    if cached is not None:
        checked_at = cached.get("checked_at", 0)
        if now - checked_at < UPDATE_CHECK_INTERVAL:
            # Cache is fresh, return cached result
            latest = cached.get("latest")
            return latest if latest else None

    # If checking is disabled, return cached result (even if stale) without network call
    if not enabled:
        if cached is not None:
            latest = cached.get("latest")
            return latest if latest else None
        return None

    # Cache is stale or missing: do a network check
    latest = check_for_update(current, fetch=fetch)

    # Save the result to cache
    save_cached_check(latest, now)

    return latest
