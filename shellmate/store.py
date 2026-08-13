"""Escalation state persistence.

Losing this file costs at most one escalation cycle, so every failure path
degrades silently rather than interrupting the pane.
"""

import contextlib
import json
import os
from pathlib import Path

from shellmate import characters
from shellmate.identity import Identity
from shellmate.models import EscalationState


def _legacy_path() -> Path:
    """Return the legacy herdr-buddy state path (pre-rename)."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "herdr-buddy" / "state.json"


def default_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shellmate" / "state.json"


def identity_path() -> Path:
    """Return the path to the identity file. Identity is write-once and precious."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shellmate" / "identity.json"


def _migrate_identity_if_needed(identity_file: Path) -> None:
    """Migrate identity from state file to dedicated identity file.

    Three cases:
    1. identity.json already exists -> do nothing, it is canonical
    2. state.json exists with embedded identity -> lift it to identity.json
    3. legacy herdr-buddy/state.json exists with identity -> lift it to identity.json

    Migration failures degrade silently (do not raise) but DO move corrupt identity
    files aside so they can be recovered and we don't silently mint a new buddy.
    """
    if identity_file.exists():
        # Identity file already exists in new location. Try to load it.
        # If it's corrupt, move it aside so we can mint a fresh one.
        try:
            raw = json.loads(identity_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and _is_valid_identity_dict(raw):
                # Valid identity already exists, nothing to do
                return
        except (OSError, ValueError, UnicodeDecodeError):
            pass

        # If we reach here, identity.json exists but is corrupt.
        # Move it aside so we can mint a fresh identity.
        try:
            corrupt_path = identity_file.parent / (identity_file.name + ".corrupt")
            identity_file.rename(corrupt_path)
        except (OSError, ValueError):
            # If we can't even move it, that's a permission issue. Log it and continue.
            pass
        return

    # Check new location state file (case 2)
    state_file = identity_file.parent / "state.json"
    if state_file.exists():
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                identity_data = raw.get("identity")
                if isinstance(identity_data, dict) and _is_valid_identity_dict(identity_data):
                    identity = _build_identity_from_dict(identity_data)
                    if identity is not None:
                        save_identity(identity_file, identity)
                        return
        except (OSError, ValueError, UnicodeDecodeError):
            pass

    # Check legacy herdr-buddy path (case 3)
    legacy = _legacy_path()
    if legacy.exists():
        try:
            raw = json.loads(legacy.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                identity_data = raw.get("identity")
                if isinstance(identity_data, dict) and _is_valid_identity_dict(identity_data):
                    identity = _build_identity_from_dict(identity_data)
                    if identity is not None:
                        save_identity(identity_file, identity)
                        return
        except (OSError, ValueError, UnicodeDecodeError):
            pass


def _is_valid_identity_dict(data: dict) -> bool:
    """Check if a dict has the required fields for a valid identity."""
    if not isinstance(data, dict):
        return False
    seed = data.get("seed")
    name = data.get("name")
    species = data.get("species")
    born_at = data.get("born_at")
    is_valid_born = isinstance(born_at, (int, float)) and not isinstance(born_at, bool)
    return (
        isinstance(seed, str)
        and isinstance(name, str)
        and isinstance(species, str)
        and is_valid_born
    )


def _build_identity_from_dict(data: dict) -> Identity | None:
    """Build an Identity from a dict, or None if invalid."""
    if not _is_valid_identity_dict(data):
        return None
    try:
        return Identity(
            seed=data["seed"],
            name=data["name"],
            species=data["species"],
            born_at=float(data["born_at"]),
        )
    except (ValueError, TypeError, KeyError):
        return None


def _migrate_state_if_needed(path: Path) -> None:
    """Migrate state from legacy herdr-buddy path if new path doesn't exist.

    On load, if the new state path does not exist and the old path does, read
    the old file, write it to the new location. The old file is left in place
    to allow recovery if migration fails. Migration failures degrade silently
    to "start fresh" rather than raising.
    """
    if path.exists():
        # New path already exists, no migration needed
        return

    legacy = _legacy_path()
    if not legacy.exists():
        # No legacy state to migrate
        return

    try:
        legacy_content = legacy.read_text(encoding="utf-8")
        # Create parent directory for new path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(legacy_content, encoding="utf-8")
    except (OSError, ValueError, UnicodeDecodeError):
        # Migration failed; fall back to "start fresh" by doing nothing
        # The new path still doesn't exist, so load() will return EscalationState()
        pass


def load_identity(path: Path) -> Identity | None:
    """Load identity from the identity file, with migration support.

    Returns the persisted Identity if it exists and is valid, or None if:
    - File doesn't exist
    - File is corrupt (moved aside as .corrupt)
    - Identity is incomplete or invalid

    Handles three migration cases:
    1. identity.json exists -> use it
    2. state.json contains embedded identity -> lift it
    3. legacy herdr-buddy/state.json contains identity -> lift it
    """
    path = Path(path)
    _migrate_identity_if_needed(path)

    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None

    return _build_identity_from_dict(raw)


def save_identity(path: Path, identity: Identity) -> None:
    """Save identity atomically, refusing to overwrite an existing valid identity.

    This is write-once in practice: if an identity file already exists and is valid,
    this function silently does nothing. Minting happens only when there is genuinely
    no identity. This makes the write-once guarantee explicit rather than relying on
    callers to be careful.

    Never raises. Failures degrade silently.
    """
    path = Path(path)

    # Check if a valid identity already exists
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and _is_valid_identity_dict(raw):
                # Valid identity exists, refuse to overwrite
                return
        except (OSError, ValueError, UnicodeDecodeError):
            # Corrupt file; we'll overwrite it below
            pass

    # Write the new identity atomically via tmp + rename
    payload = {
        "seed": identity.seed,
        "name": identity.name,
        "species": identity.species,
        "born_at": identity.born_at,
    }
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def load(path: Path) -> EscalationState:
    path = Path(path)
    _migrate_state_if_needed(path)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return EscalationState()
    if not isinstance(raw, dict):
        return EscalationState()

    try:
        waiting = raw.get("waiting_since")
        notified = raw.get("notified")
        last = raw.get("last_alert_at")
        last_st = raw.get("last_status")
        petted = raw.get("petted_at")
        pet_cnt = raw.get("pet_count")
        phrase_text = raw.get("phrase_text")
        phrase_set_at = raw.get("phrase_set_at")
        last_mood_raw = raw.get("last_mood")
        mood_since_raw = raw.get("mood_since")
        phrase_by_session_raw = raw.get("phrase_by_session")
        phrase_set_at_by_session_raw = raw.get("phrase_set_at_by_session")
        last_mood_by_session_raw = raw.get("last_mood_by_session")

        # Validate waiting_since: only keep str keys with float/int values (excluding bool)
        waiting_since_validated = {}
        if isinstance(waiting, dict):
            for k, v in waiting.items():
                is_num = isinstance(v, (int, float)) and not isinstance(v, bool)
                if isinstance(k, str) and is_num:
                    with contextlib.suppress(ValueError, TypeError):
                        waiting_since_validated[k] = float(v)

        # Validate notified: only keep str keys with list values containing only strings
        notified_validated = {}
        if isinstance(notified, dict):
            for k, v in notified.items():
                if isinstance(k, str) and isinstance(v, list):
                    with contextlib.suppress(ValueError, TypeError):
                        notified_validated[k] = [item for item in v if isinstance(item, str)]

        is_valid_last = isinstance(last, (int, float)) and not isinstance(last, bool)
        last_alert_at = float(last) if is_valid_last else 0.0

        # Validate last_status: only keep str keys with str values
        last_status_validated = {}
        if isinstance(last_st, dict):
            for k, v in last_st.items():
                if isinstance(k, str) and isinstance(v, str):
                    last_status_validated[k] = v

        # Validate petted_at: must be a number (float/int, not bool) or None
        petted_at_validated = None
        if petted is not None:
            is_num = isinstance(petted, (int, float)) and not isinstance(petted, bool)
            if is_num:
                with contextlib.suppress(ValueError, TypeError):
                    petted_at_validated = float(petted)

        # Validate pet_count: must be an int, default 0
        pet_count_validated = 0
        if isinstance(pet_cnt, int) and not isinstance(pet_cnt, bool):
            pet_count_validated = max(0, pet_cnt)

        # Validate phrase_text: must be a string, default ""
        phrase_text_validated = ""
        if isinstance(phrase_text, str):
            phrase_text_validated = phrase_text

        # Validate phrase_set_at: must be a number (float/int, not bool), default 0.0
        phrase_set_at_validated = 0.0
        is_valid_phrase_set_at = isinstance(phrase_set_at, (int, float)) and not isinstance(
            phrase_set_at, bool
        )
        if is_valid_phrase_set_at:
            with contextlib.suppress(ValueError, TypeError):
                phrase_set_at_validated = float(phrase_set_at)

        # Validate last_mood: must be a known mood, default "sleeping".
        # This one is load-bearing. escalation.advance() re-picks the phrase when
        # the mood ENTERS a signal mood from a non-signal one, and it reads that
        # "from" value here. While last_mood was not persisted it reloaded as
        # "sleeping" on every call, so a buddy sitting in alert looked like it was
        # entering alert afresh twice a second and the phrase never held still.
        last_mood_validated = "sleeping"
        if isinstance(last_mood_raw, str) and last_mood_raw in characters.MOODS:
            last_mood_validated = last_mood_raw

        # Validate mood_since: must be a number (float/int, not bool), default 0.0
        mood_since_validated = 0.0
        is_valid_mood_since = isinstance(mood_since_raw, (int, float)) and not isinstance(
            mood_since_raw, bool
        )
        if is_valid_mood_since:
            with contextlib.suppress(ValueError, TypeError):
                mood_since_validated = float(mood_since_raw)

        # Per-session phrase slots. Same validation shape as last_status: keep only
        # str->str (or str->float) entries and drop anything malformed, so a junk
        # file degrades to "no remembered phrase" rather than losing the whole state.
        phrase_by_session_validated = {}
        if isinstance(phrase_by_session_raw, dict):
            for k, v in phrase_by_session_raw.items():
                if isinstance(k, str) and isinstance(v, str):
                    phrase_by_session_validated[k] = v

        phrase_set_at_by_session_validated = {}
        if isinstance(phrase_set_at_by_session_raw, dict):
            for k, v in phrase_set_at_by_session_raw.items():
                is_num = isinstance(v, (int, float)) and not isinstance(v, bool)
                if isinstance(k, str) and is_num:
                    with contextlib.suppress(ValueError, TypeError):
                        phrase_set_at_by_session_validated[k] = float(v)

        last_mood_by_session_validated = {}
        if isinstance(last_mood_by_session_raw, dict):
            for k, v in last_mood_by_session_raw.items():
                if isinstance(k, str) and isinstance(v, str) and v in characters.MOODS:
                    last_mood_by_session_validated[k] = v

        return EscalationState(
            waiting_since=waiting_since_validated,
            notified=notified_validated,
            last_alert_at=last_alert_at,
            last_status=last_status_validated,
            petted_at=petted_at_validated,
            pet_count=pet_count_validated,
            phrase_text=phrase_text_validated,
            phrase_set_at=phrase_set_at_validated,
            last_mood=last_mood_validated,
            mood_since=mood_since_validated,
            phrase_by_session=phrase_by_session_validated,
            phrase_set_at_by_session=phrase_set_at_by_session_validated,
            last_mood_by_session=last_mood_by_session_validated,
        )
    except Exception:
        return EscalationState()


def save(path: Path, state: EscalationState) -> None:
    """Write escalation state atomically via tmp + rename. Never raises.

    Identity is NOT saved here — it lives in a separate identity.json file.
    This prevents escalation timer writes from touching the precious, write-once identity.
    """
    path = Path(path)
    payload = {
        "waiting_since": state.waiting_since,
        "notified": state.notified,
        "last_alert_at": state.last_alert_at,
        "last_status": state.last_status,
        "petted_at": state.petted_at,
        "pet_count": state.pet_count,
        "phrase_text": state.phrase_text,
        "phrase_set_at": state.phrase_set_at,
        "last_mood": state.last_mood,
        "mood_since": state.mood_since,
        "phrase_by_session": state.phrase_by_session,
        "phrase_set_at_by_session": state.phrase_set_at_by_session,
        "last_mood_by_session": state.last_mood_by_session,
    }
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
