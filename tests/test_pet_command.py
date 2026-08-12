"""Tests for the --pet command and petting state persistence."""

from shellmate.app import main
from shellmate.identity import Identity
from shellmate.store import load, save_identity


def test_pet_command_returns_zero(tmp_path, monkeypatch):
    """Verify that --pet command exits with 0."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    result = main(["--pet"])
    assert result == 0


def test_pet_command_prints_one_line(tmp_path, monkeypatch, capsys):
    """Verify that --pet command prints exactly one line."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    main(["--pet"])
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"


def test_pet_command_cat_purrs(tmp_path, monkeypatch, capsys):
    """Verify that cat buddy purrs when petted."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create a cat identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    main(["--pet"])
    captured = capsys.readouterr()
    assert "purrs softly" in captured.out


def test_pet_command_dog_wags(tmp_path, monkeypatch, capsys):
    """Verify that dog buddy wags tail when petted."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create a dog identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Rex",
        species="dog",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    main(["--pet"])
    captured = capsys.readouterr()
    assert "wags tail happily" in captured.out


def test_pet_command_owl_hoots(tmp_path, monkeypatch, capsys):
    """Verify that owl buddy hoots when petted."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create an owl identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Hoot",
        species="owl",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    main(["--pet"])
    captured = capsys.readouterr()
    assert "hoots softly" in captured.out


def test_pet_command_blob_wobbles(tmp_path, monkeypatch, capsys):
    """Verify that blob buddy wobbles when petted."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create a blob identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Blobby",
        species="blob",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    main(["--pet"])
    captured = capsys.readouterr()
    assert "wobbles gently" in captured.out


def test_pet_command_increments_pet_count(tmp_path, monkeypatch):
    """Verify that petting increments the pet count."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet once
    main(["--pet"])
    state = load(tmp_path / "shellmate" / "state.json")
    assert state.pet_count == 1

    # Pet again
    main(["--pet"])
    state = load(tmp_path / "shellmate" / "state.json")
    assert state.pet_count == 2


def test_pet_command_sets_petted_at_timestamp(tmp_path, monkeypatch):
    """Verify that petting sets the petted_at timestamp."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    import time

    before_pet = time.time()
    main(["--pet"])
    after_pet = time.time()

    state = load(tmp_path / "shellmate" / "state.json")
    assert state.petted_at is not None
    assert before_pet <= state.petted_at <= after_pet


def test_pet_count_persists_across_invocations(tmp_path, monkeypatch):
    """Verify that pet count persists across multiple --pet invocations."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet three times
    for _ in range(3):
        main(["--pet"])

    state = load(tmp_path / "shellmate" / "state.json")
    assert state.pet_count == 3


def test_whoami_shows_pet_count_when_nonzero(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows pet count when pet_count > 0."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet a couple times
    main(["--pet"])
    main(["--pet"])

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "petted 2 times" in captured.out


def test_whoami_omits_pet_count_when_zero(tmp_path, monkeypatch, capsys):
    """Verify that --whoami omits pet count when pet_count == 0."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity without petting
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "petted" not in captured.out


def test_whoami_shows_egg_stage(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows egg stage for very young buddies."""
    import time

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create a very fresh identity (less than 8 hours old)
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=now - 3600.0,  # 1 hour old
    )
    save_identity(identity_file, identity)

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "(egg)" in captured.out


def test_whoami_shows_hatchling_stage(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows hatchling stage for 8h-2d old buddies."""
    import time

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create an identity between 8 hours and 2 days old
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=now - (12 * 3600.0),  # 12 hours old
    )
    save_identity(identity_file, identity)

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "(hatchling)" in captured.out


def test_whoami_shows_juvenile_stage(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows juvenile stage for 2d-4d old buddies."""
    import time

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create an identity between 2 days and 4 days old
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=now - (3 * 86400.0),  # 3 days old
    )
    save_identity(identity_file, identity)

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "(juvenile)" in captured.out


def test_whoami_shows_adult_stage_at_4_days(tmp_path, monkeypatch, capsys):
    """Verify that --whoami omits stage label for adult buddies (4+ days old)."""
    import time

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create an older identity (more than 4 days old)
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=now - (5 * 86400.0),  # 5 days old
    )
    save_identity(identity_file, identity)

    # Check --whoami output
    main(["--whoami"])
    captured = capsys.readouterr()
    # Should not show any stage label for adults
    assert "(egg)" not in captured.out
    assert "(hatchling)" not in captured.out
    assert "(juvenile)" not in captured.out


def test_pet_counter_increments_correctly(tmp_path, monkeypatch):
    """Verify that petting increments the counter correctly each time."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet 5 times and verify count reaches 5
    for i in range(5):
        main(["--pet"])
        state = load(tmp_path / "shellmate" / "state.json")
        assert state.pet_count == i + 1, f"After {i + 1} pets, count should be {i + 1}"


def test_whoami_grammar_one_time(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows 'petted 1 time' (singular) not 'times'."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet once
    main(["--pet"])

    # Check --whoami output for singular
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "petted 1 time" in captured.out
    assert "petted 1 times" not in captured.out


def test_whoami_grammar_multiple_times(tmp_path, monkeypatch, capsys):
    """Verify that --whoami shows 'petted N times' (plural) for N > 1."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    # Create initial identity
    identity_file = tmp_path / "shellmate" / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity = Identity(
        seed="test-seed",
        name="Whiskers",
        species="cat",
        born_at=0.0,
    )
    save_identity(identity_file, identity)

    # Pet three times
    for _ in range(3):
        main(["--pet"])

    # Check --whoami output for plural
    main(["--whoami"])
    captured = capsys.readouterr()
    assert "petted 3 times" in captured.out
