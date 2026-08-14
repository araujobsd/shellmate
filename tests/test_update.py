"""Tests for update checking and version comparison."""

import json

from shellmate.update import (
    _parse_version,
    check_for_update,
    check_for_update_cached,
    load_cached_check,
    save_cached_check,
)


class TestParseVersion:
    """Test version string parsing."""

    def test_parse_simple_version(self):
        """Parse '0.1.0' -> (0, 1, 0)."""
        assert _parse_version("0.1.0") == (0, 1, 0)

    def test_parse_version_with_v_prefix(self):
        """Strip leading 'v' from versions."""
        assert _parse_version("v0.1.0") == (0, 1, 0)

    def test_parse_two_part_version(self):
        """Parse '1.2' -> (1, 2)."""
        assert _parse_version("1.2") == (1, 2)

    def test_parse_single_part_version(self):
        """Parse '5' -> (5,)."""
        assert _parse_version("5") == (5,)

    def test_parse_large_numbers(self):
        """Parse '0.10.0' correctly, not confused by order."""
        assert _parse_version("0.10.0") == (0, 10, 0)

    def test_parse_fails_for_non_numeric(self):
        """Return None for non-numeric version."""
        assert _parse_version("vfoo") is None
        assert _parse_version("1.2.x") is None

    def test_parse_fails_for_empty_string(self):
        """Return None for empty string."""
        assert _parse_version("") is None

    def test_parse_fails_for_none(self):
        """Return None for None input."""
        assert _parse_version(None) is None


class TestVersionComparison:
    """Test that versions compare correctly (older < newer)."""

    def test_older_version_is_less(self):
        """0.1.0 < 0.2.0."""
        old = _parse_version("0.1.0")
        new = _parse_version("0.2.0")
        assert old < new

    def test_minor_version_comparison(self):
        """0.9.0 < 0.10.0 (numeric, not lexical)."""
        v9 = _parse_version("0.9.0")
        v10 = _parse_version("0.10.0")
        assert v9 < v10

    def test_equal_versions(self):
        """0.1.0 == 0.1.0."""
        assert _parse_version("0.1.0") == _parse_version("0.1.0")

    def test_major_version_comparison(self):
        """1.0.0 > 0.9.9."""
        v1 = _parse_version("1.0.0")
        v0 = _parse_version("0.9.9")
        assert v1 > v0


class TestCheckForUpdate:
    """Test update checking without caching."""

    def test_newer_version_detected(self):
        """Return newer version when available."""

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.2.0"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result == "0.2.0"

    def test_same_version_returns_none(self):
        """Return None when versions are equal."""

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.1.0"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_older_version_returns_none(self):
        """Return None when remote is older."""

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.0.9"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_no_releases_403_returns_none(self):
        """No releases (403/404) treated silently as no update."""

        def mock_fetch(url, timeout):
            raise OSError("403")

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_network_error_returns_none(self):
        """Network errors are silent, return None."""

        def mock_fetch(url, timeout):
            raise OSError("Connection refused")

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_timeout_returns_none(self):
        """Timeouts return None silently."""

        def mock_fetch(url, timeout):
            raise TimeoutError()

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_malformed_json_returns_none(self):
        """Malformed JSON returns None silently."""

        def mock_fetch(url, timeout):
            raise json.JSONDecodeError("msg", "doc", 0)

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_missing_tag_name_returns_none(self):
        """Missing tag_name in response returns None."""

        def mock_fetch(url, timeout):
            return {"wrong_key": "value"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_empty_response_returns_none(self):
        """Empty response returns None."""

        def mock_fetch(url, timeout):
            return {}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_unparseable_remote_version_returns_none(self):
        """Unparseable remote version returns None."""

        def mock_fetch(url, timeout):
            return {"tag_name": "vfoo"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result is None

    def test_unparseable_current_version_returns_none(self):
        """Unparseable current version returns None."""

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.2.0"}

        result = check_for_update("invalid", fetch=mock_fetch)
        assert result is None

    def test_v_prefix_stripped_from_result(self):
        """'v' prefix is stripped from returned version."""

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.2.0"}

        result = check_for_update("0.1.0", fetch=mock_fetch)
        assert result == "0.2.0"
        assert not result.startswith("v")


class TestCaching:
    """Test cache loading and saving."""

    def test_cache_is_saved(self, tmp_path, monkeypatch):
        """Cache is written to disk."""
        # Redirect cache path to tmp
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        save_cached_check("0.2.0", 1000.0)

        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert data["latest"] == "0.2.0"
        assert data["checked_at"] == 1000

    def test_cache_loads_correctly(self, tmp_path, monkeypatch):
        """Cache is read from disk."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        data = {"checked_at": 1000, "latest": "0.2.0"}
        cache_path.write_text(json.dumps(data))

        loaded = load_cached_check()
        assert loaded == data

    def test_missing_cache_returns_none(self, tmp_path, monkeypatch):
        """Missing cache file returns None."""
        monkeypatch.setattr(
            "shellmate.update.get_cache_path", lambda: tmp_path / "nonexistent.json"
        )

        result = load_cached_check()
        assert result is None

    def test_corrupt_cache_returns_none(self, tmp_path, monkeypatch):
        """Corrupt cache file returns None, never raises."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("not valid json {{{")

        result = load_cached_check()
        assert result is None

    def test_cache_honored_within_interval(self, tmp_path, monkeypatch):
        """Cache is used if still fresh (< 24 hours old)."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        now = 2000.0
        checked_at = 1000.0  # 1000 seconds ago

        # Save cache
        save_cached_check("0.2.0", checked_at)

        # Mock fetch that would fail
        fetch_called = False

        def mock_fetch(url, timeout):
            nonlocal fetch_called
            fetch_called = True
            raise OSError("Should not be called")

        result = check_for_update_cached("0.1.0", now, fetch=mock_fetch)

        # Fetch should not have been called; cache was fresh
        assert not fetch_called
        assert result == "0.2.0"

    def test_cache_refreshed_after_interval(self, tmp_path, monkeypatch):
        """Cache is refreshed after 24 hours."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Save old cache (25 hours old)
        old_checked = 1000.0
        now = old_checked + 90000  # 25 hours later

        save_cached_check("0.1.5", old_checked)

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.2.0"}

        result = check_for_update_cached("0.1.0", now, fetch=mock_fetch)

        # Should have refreshed and found new version
        assert result == "0.2.0"

        # New cache should be saved
        data = json.loads(cache_path.read_text())
        assert data["latest"] == "0.2.0"
        assert data["checked_at"] == int(now)

    def test_none_result_also_cached(self, tmp_path, monkeypatch):
        """None results (no update) are also cached."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        now = 2000.0

        def mock_fetch(url, timeout):
            return {"tag_name": "v0.1.0"}  # Same version, no update

        result = check_for_update_cached("0.1.0", now, fetch=mock_fetch)

        assert result is None

        # Cache should have None for latest
        data = json.loads(cache_path.read_text())
        assert data["latest"] is None
        assert data["checked_at"] == int(now)


class TestGating:
    """Test that check_updates config flag gates network calls."""

    def test_enabled_false_prevents_network_call(self, tmp_path, monkeypatch):
        """When enabled=False, no network call is made even with stale cache."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Create old (stale) cache
        save_cached_check("0.1.5", 0.0)

        # Track whether fetch was called
        fetch_called = False

        def mock_fetch(url, timeout):
            nonlocal fetch_called
            fetch_called = True
            return {"tag_name": "v0.2.0"}

        # Call with enabled=False and stale cache
        now = 100000.0  # Well past the 24h interval
        result = check_for_update_cached("0.1.0", now, fetch=mock_fetch, enabled=False)

        # Fetch should NOT have been called
        assert not fetch_called, "Network call was made when enabled=False"
        # Should return cached result
        assert result == "0.1.5"

    def test_enabled_false_with_fresh_cache(self, tmp_path, monkeypatch):
        """With enabled=False and fresh cache, return cached result."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")
        cache_path = tmp_path / "update.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Create fresh cache
        now = 1000.0
        save_cached_check("0.2.0", now)

        fetch_called = False

        def mock_fetch(url, timeout):
            nonlocal fetch_called
            fetch_called = True
            raise Exception("Should not be called")

        # Call with enabled=False and fresh cache
        result = check_for_update_cached("0.1.0", now, fetch=mock_fetch, enabled=False)

        assert not fetch_called, "Network call was made when enabled=False"
        assert result == "0.2.0"

    def test_enabled_false_with_no_cache(self, tmp_path, monkeypatch):
        """With enabled=False and no cache, return None without network call."""
        monkeypatch.setattr("shellmate.update.get_cache_path", lambda: tmp_path / "update.json")

        fetch_called = False

        def mock_fetch(url, timeout):
            nonlocal fetch_called
            fetch_called = True
            raise Exception("Should not be called")

        result = check_for_update_cached("0.1.0", 1000.0, fetch=mock_fetch, enabled=False)

        assert not fetch_called, "Network call was made when enabled=False"
        assert result is None


def test_declared_version_is_not_behind_the_newest_release_tag():
    """A tag ahead of __version__ makes every up-to-date install nag forever.

    v2.0.0 was tagged while __version__ still read 1.5.0. check_for_update
    compares the newest GitHub release against __version__, so it kept returning
    "2.0.0 is available" no matter how current the install actually was — and
    nothing in the suite noticed, because the version is only ever read, never
    checked against the thing it is supposed to track.

    Skipped where git or the tags are not available (sdist, shallow clone), so
    this guards the release process rather than gating unrelated work.
    """
    import pathlib
    import subprocess

    import pytest

    from shellmate import __version__
    from shellmate.update import _parse_version

    repo = pathlib.Path(__file__).resolve().parents[1]
    try:
        proc = subprocess.run(
            ["git", "tag", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            cwd=repo,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - env dependent
        pytest.skip("git is not available")
    if proc.returncode != 0 or not proc.stdout.strip():  # pragma: no cover
        pytest.skip("no tags in this checkout")

    tags = [_parse_version(t) for t in proc.stdout.split()]
    newest = max((t for t in tags if t is not None), default=None)
    if newest is None:  # pragma: no cover
        pytest.skip("no parseable version tags")

    declared = _parse_version(__version__)
    assert declared is not None, f"__version__ {__version__!r} does not parse"
    assert declared >= newest, (
        f"__version__ is {__version__}, but {'.'.join(str(p) for p in newest)} is tagged. "
        "The update check compares releases against __version__, so every current "
        "install would be told to update."
    )
