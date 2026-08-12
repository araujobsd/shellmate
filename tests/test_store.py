import json

from shellmate.identity import Identity
from shellmate.models import EscalationState
from shellmate.store import default_path, identity_path, load, load_identity, save, save_identity


def test_missing_file_yields_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state = load(tmp_path / "absent.json")
    assert state.waiting_since == {}
    assert state.notified == {}
    assert state.last_alert_at == 0.0


def test_round_trip(tmp_path):
    p = tmp_path / "state.json"
    original = EscalationState({"a": 100.0}, {"a": ["HIGH"]}, 250.0)
    save(p, original)
    restored = load(p)
    assert restored.waiting_since == {"a": 100.0}
    assert restored.notified == {"a": ["HIGH"]}
    assert restored.last_alert_at == 250.0


def test_corrupt_file_yields_empty_state(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{{{ not json")
    assert load(p).waiting_since == {}


def test_wrong_shape_yields_empty_state(tmp_path):
    p = tmp_path / "state.json"
    p.write_text('["a", "list", "not", "an", "object"]')
    assert load(p).waiting_since == {}


def test_save_creates_parent_directories(tmp_path):
    p = tmp_path / "nested" / "deeper" / "state.json"
    save(p, EscalationState())
    assert p.exists()


def test_save_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "state.json"
    save(p, EscalationState({"a": 1.0}, {}, 0.0))
    assert [f.name for f in tmp_path.iterdir()] == ["state.json"]


def test_save_overwrites_cleanly(tmp_path):
    p = tmp_path / "state.json"
    save(p, EscalationState({"a": 1.0}, {}, 0.0))
    save(p, EscalationState({"b": 2.0}, {}, 0.0))
    assert load(p).waiting_since == {"b": 2.0}


def test_save_failure_is_swallowed(tmp_path):
    # a directory where the file should be — save must not raise
    p = tmp_path / "state.json"
    p.mkdir()
    save(p, EscalationState())


def test_default_path_respects_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert default_path() == tmp_path / "shellmate" / "state.json"


def test_waiting_since_value_is_dict_yields_empty_state(tmp_path):
    p = tmp_path / "state.json"
    p.write_text('{"waiting_since": {"a": {"b": 1}}, "notified": {}, "last_alert_at": 0}')
    assert load(p).waiting_since == {}


def test_waiting_since_value_is_string_yields_empty_state(tmp_path):
    p = tmp_path / "state.json"
    p.write_text('{"waiting_since": {"a": "not_a_float"}, "notified": {}, "last_alert_at": 0}')
    assert load(p).waiting_since == {}


def test_notified_value_is_string_skips_entry(tmp_path):
    p = tmp_path / "state.json"
    p.write_text('{"waiting_since": {}, "notified": {"a": "HIGH"}, "last_alert_at": 0}')
    assert load(p).notified == {}


def test_notified_list_with_non_strings_drops_non_strings(tmp_path):
    p = tmp_path / "state.json"
    data = '{"waiting_since": {}, "notified": {"a": ["HIGH", 123, "CRIT"]}, "last_alert_at": 0}'
    p.write_text(data)
    assert load(p).notified == {"a": ["HIGH", "CRIT"]}


def test_mixed_valid_and_invalid_entries_keeps_valid(tmp_path):
    p = tmp_path / "state.json"
    data = (
        '{"waiting_since": {"good": 100.5, "bad": "string"}, '
        '"notified": {"ok": ["HIGH"], "nope": "nope"}, "last_alert_at": 0}'
    )
    p.write_text(data)
    state = load(p)
    assert state.waiting_since == {"good": 100.5}
    assert state.notified == {"ok": ["HIGH"]}


def test_missing_identity_section_loads_fine(tmp_path):
    """State file with no identity section loads successfully."""
    p = tmp_path / "state.json"
    p.write_text('{"waiting_since": {}, "notified": {}, "last_alert_at": 0}')
    state = load(p)
    assert state.waiting_since == {}


# ===== New tests for identity separation =====


def test_identity_path_respects_xdg(monkeypatch, tmp_path):
    """identity_path() respects XDG_STATE_HOME."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert identity_path() == tmp_path / "shellmate" / "identity.json"


def test_save_bare_state_does_not_touch_identity(tmp_path, monkeypatch):
    """Saving a bare EscalationState does NOT affect identity.json.

    This is the exact bug that was reported: calling save() with a bare
    EscalationState must not overwrite the identity.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state_path = tmp_path / "shellmate" / "state.json"
    ident_path = tmp_path / "shellmate" / "identity.json"

    # Save an identity first
    identity = Identity(seed="abc", name="Kukeme", species="blob", born_at=1000.0)
    save_identity(ident_path, identity)
    original_content = ident_path.read_text()

    # Save a bare state 50 times
    for _ in range(50):
        save(state_path, EscalationState())

    # Identity must be unchanged
    assert ident_path.read_text() == original_content
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "Kukeme"


def test_save_identity_refuses_overwrite(tmp_path):
    """save_identity refuses to overwrite an existing valid identity."""
    ident_path = tmp_path / "identity.json"

    # Save first identity
    identity1 = Identity(seed="abc123", name="Miso", species="cat", born_at=100.0)
    save_identity(ident_path, identity1)
    original_content = ident_path.read_text()

    # Try to save a different identity
    identity2 = Identity(seed="xyz789", name="Tobek", species="dog", born_at=200.0)
    save_identity(ident_path, identity2)

    # Original identity must still be there (not overwritten)
    assert ident_path.read_text() == original_content
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "Miso"
    assert restored.species == "cat"


def test_load_identity_missing_file_returns_none(tmp_path):
    """load_identity returns None when file doesn't exist."""
    ident_path = tmp_path / "identity.json"
    result = load_identity(ident_path)
    assert result is None


def test_load_identity_corrupt_file_moves_aside(tmp_path):
    """Corrupt identity.json is moved to identity.json.corrupt."""
    ident_path = tmp_path / "identity.json"
    corrupt_path = tmp_path / "identity.json.corrupt"

    # Write corrupt identity file
    ident_path.write_text("{not valid json")

    # Load should return None and move the file
    result = load_identity(ident_path)
    assert result is None
    assert not ident_path.exists()
    assert corrupt_path.exists()
    assert corrupt_path.read_text() == "{not valid json"


def test_identity_round_trip(tmp_path):
    """Identity persists across save/load."""
    ident_path = tmp_path / "identity.json"
    identity = Identity(seed="abc123", name="Miso", species="cat", born_at=100.0)
    save_identity(ident_path, identity)
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.seed == "abc123"
    assert restored.name == "Miso"
    assert restored.species == "cat"
    assert restored.born_at == 100.0


def test_migration_case_b_state_with_embedded_identity(tmp_path, monkeypatch):
    """Migration case (b): state.json with embedded identity lifts to identity.json.

    When loading identity, if identity.json doesn't exist but state.json does
    with an embedded identity block, lift it to identity.json.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state_path = tmp_path / "shellmate" / "state.json"
    ident_path = tmp_path / "shellmate" / "identity.json"

    # Create state file with embedded identity
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_data = {
        "waiting_since": {"agent1": 50.0},
        "notified": {},
        "last_alert_at": 0.0,
        "identity": {
            "seed": "migration-test",
            "name": "Zifamu",
            "species": "cat",
            "born_at": 100.0,
        },
    }
    state_path.write_text(json.dumps(state_data))

    # Load identity (should migrate from state.json)
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "Zifamu"
    assert restored.species == "cat"
    assert restored.seed == "migration-test"
    assert restored.born_at == 100.0

    # identity.json should now exist
    assert ident_path.exists()


def test_migration_case_c_legacy_herdr_buddy_path(tmp_path, monkeypatch):
    """Migration case (c): legacy herdr-buddy/state.json with embedded identity lifts.

    When loading identity, if both identity.json and state.json are missing
    but legacy herdr-buddy/state.json exists with an identity, lift it.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    legacy_path = tmp_path / "herdr-buddy" / "state.json"
    ident_path = tmp_path / "shellmate" / "identity.json"

    # Create legacy file with embedded identity
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_data = {
        "waiting_since": {"agent1": 50.0},
        "notified": {},
        "last_alert_at": 0.0,
        "identity": {
            "seed": "legacy-test",
            "name": "Legatus",
            "species": "bird",
            "born_at": 500.0,
        },
    }
    legacy_path.write_text(json.dumps(legacy_data))

    # Load identity (should migrate from legacy path)
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "Legatus"
    assert restored.species == "bird"
    assert restored.seed == "legacy-test"
    assert restored.born_at == 500.0

    # identity.json should now exist
    assert ident_path.exists()


def test_migration_prefers_identity_file_over_state(tmp_path, monkeypatch):
    """If identity.json exists, state.json embedded identity is ignored."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state_path = tmp_path / "shellmate" / "state.json"
    ident_path = tmp_path / "shellmate" / "identity.json"

    # Create both identity.json and state.json with different identities
    ident_path.parent.mkdir(parents=True, exist_ok=True)
    identity1 = Identity(seed="prefer-me", name="First", species="cat", born_at=100.0)
    save_identity(ident_path, identity1)

    state_data = {
        "waiting_since": {},
        "notified": {},
        "last_alert_at": 0.0,
        "identity": {
            "seed": "ignore-me",
            "name": "Second",
            "species": "dog",
            "born_at": 200.0,
        },
    }
    state_path.write_text(json.dumps(state_data))

    # Load should return the identity from identity.json, not state.json
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "First"
    assert restored.species == "cat"


def test_state_does_not_include_identity_field(tmp_path):
    """EscalationState.save does NOT include identity in the JSON payload."""
    state_path = tmp_path / "state.json"
    state = EscalationState(
        waiting_since={"a": 100.0},
        notified={"a": ["HIGH"]},
        last_alert_at=250.0,
    )
    save(state_path, state)

    # Read the JSON and verify no identity field
    raw = json.loads(state_path.read_text())
    assert "identity" not in raw
    assert raw == {
        "waiting_since": {"a": 100.0},
        "notified": {"a": ["HIGH"]},
        "last_alert_at": 250.0,
        "last_status": {},
        "petted_at": None,
        "pet_count": 0,
    }


def test_concurrent_state_saves_preserve_identity(tmp_path, monkeypatch):
    """Rapid sequential state saves don't corrupt identity.

    This simulates the high-frequency state saves from the sprite script
    while identity is in a separate file.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state_path = tmp_path / "shellmate" / "state.json"
    ident_path = tmp_path / "shellmate" / "identity.json"

    # Save identity once
    identity = Identity(seed="stable", name="Companion", species="blob", born_at=1000.0)
    save_identity(ident_path, identity)
    original_content = ident_path.read_text()

    # Simulate many rapid state saves (sprite script runs ~10/sec)
    for i in range(100):
        new_state = EscalationState(
            waiting_since={"agent": float(i)},
            notified={},
            last_alert_at=0.0,
        )
        save(state_path, new_state)

    # Identity must be byte-identical
    assert ident_path.read_text() == original_content
    restored = load_identity(ident_path)
    assert restored is not None
    assert restored.name == "Companion"
    assert restored.species == "blob"


def test_invalid_identity_data_in_state_falls_back_to_none(tmp_path):
    """Invalid identity data in state.json doesn't create a partial identity."""
    state_path = tmp_path / "state.json"
    ident_path = tmp_path / "identity.json"

    # Create state with invalid identity (missing name)
    state_data = {
        "waiting_since": {},
        "notified": {},
        "last_alert_at": 0.0,
        "identity": {
            "seed": "incomplete",
            "species": "cat",
            "born_at": 100.0,
            # name is missing!
        },
    }
    state_path.write_text(json.dumps(state_data))

    # Migration should not create identity.json since identity is invalid
    restored = load_identity(ident_path)
    assert restored is None
    assert not ident_path.exists()
