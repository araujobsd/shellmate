"""Tests for age stages, baby sprites, and petting features."""

from shellmate.characters import (
    BABY,
    BABY_MOODS,
    CHARACTERS,
    COMPACT,
    DEFAULT_CHARACTER,
    NAMES,
    SPRITE_LINES,
    SPRITE_MAX_COLS,
    apply_petting,
    frames_for,
    stage_for,
)
from shellmate.textwidth import width


# Tests for stage_for()
def test_stage_for_returns_egg_under_8_hours():
    """Buddies under 8 hours old are eggs."""
    born_at = 1000.0
    now = born_at + 3600.0  # 1 hour later
    assert stage_for(born_at, now) == "egg"


def test_stage_for_returns_egg_at_7_hours_59_minutes():
    """Buddies at 7h59m old are still eggs."""
    born_at = 1000.0
    now = born_at + (7 * 3600.0 + 59 * 60.0)  # 7h59m later
    assert stage_for(born_at, now) == "egg"


def test_stage_for_returns_hatchling_at_8_hours():
    """Buddies at exactly 8 hours old are hatchlings."""
    born_at = 1000.0
    now = born_at + (8 * 3600.0)  # 8 hours later
    assert stage_for(born_at, now) == "hatchling"


def test_stage_for_returns_hatchling_at_1_day():
    """Buddies at 1 day old are still hatchlings."""
    born_at = 1000.0
    now = born_at + (1 * 86400.0)  # 1 day later
    assert stage_for(born_at, now) == "hatchling"


def test_stage_for_returns_juvenile_at_2_days():
    """Buddies at exactly 2 days old are juveniles."""
    born_at = 1000.0
    now = born_at + (2 * 86400.0)  # 2 days later
    assert stage_for(born_at, now) == "juvenile"


def test_stage_for_returns_juvenile_at_3_days():
    """Buddies at 3 days old are still juveniles."""
    born_at = 1000.0
    now = born_at + (3 * 86400.0)  # 3 days later
    assert stage_for(born_at, now) == "juvenile"


def test_stage_for_returns_adult_at_4_days():
    """Buddies at exactly 4 days old are adults."""
    born_at = 1000.0
    now = born_at + (4 * 86400.0)  # 4 days later
    assert stage_for(born_at, now) == "adult"


def test_stage_for_returns_adult_over_4_days():
    """Buddies over 4 days old are adults."""
    born_at = 1000.0
    now = born_at + (30 * 86400.0)  # 30 days later
    assert stage_for(born_at, now) == "adult"


def test_stage_for_is_pure():
    """stage_for is deterministic with same inputs."""
    born_at = 1000.0
    now = 1010.0
    result1 = stage_for(born_at, now)
    result2 = stage_for(born_at, now)
    assert result1 == result2


# Tests for BABY structure
def test_baby_exists():
    """BABY dict is defined."""
    assert BABY is not None
    assert isinstance(BABY, dict)


def test_baby_covers_all_characters():
    """BABY has entries for all characters."""
    for char_name in NAMES:
        assert char_name in BABY, f"BABY missing entry for {char_name}"


def test_baby_only_defines_sleeping_and_working():
    """BABY should only define sleeping and working moods."""
    for char_name, moods in BABY.items():
        assert set(moods.keys()) == set(BABY_MOODS), (
            f"BABY[{char_name}] has moods {set(moods.keys())}, expected {set(BABY_MOODS)}"
        )


def test_baby_frames_have_two_frames_each():
    """Each baby mood should have exactly 2 frames."""
    for char_name, moods in BABY.items():
        for mood, frames in moods.items():
            msg = f"BABY[{char_name}][{mood}] has {len(frames)} frames, expected 2"
            assert len(frames) == 2, msg


def test_baby_frames_have_exactly_three_lines():
    """Each baby frame should have exactly 3 lines."""
    for char_name, moods in BABY.items():
        for mood, frames in moods.items():
            for i, frame in enumerate(frames):
                msg = (
                    f"BABY[{char_name}][{mood}][{i}] has {len(frame)} lines, "
                    f"expected {SPRITE_LINES}"
                )
                assert len(frame) == SPRITE_LINES, msg


def test_baby_frames_within_column_budget():
    """Each baby frame line should be <= 12 columns."""
    for char_name, moods in BABY.items():
        for mood, frames in moods.items():
            for i, frame in enumerate(frames):
                for j, line in enumerate(frame):
                    w = width(line)
                    msg = (
                        f"BABY[{char_name}][{mood}][{i}][{j}] width {w} exceeds "
                        f"{SPRITE_MAX_COLS}: {line!r}"
                    )
                    assert w <= SPRITE_MAX_COLS, msg


def test_baby_frames_are_distinct():
    """Each baby mood should have two different frames."""
    for char_name, moods in BABY.items():
        for mood, frames in moods.items():
            assert frames[0] != frames[1], f"BABY[{char_name}][{mood}] has identical frames"


# Tests for frames_for with different stages
def test_frames_for_returns_baby_sprites_for_hatchling():
    """frames_for returns baby sprites for hatchling stage when available."""
    name = DEFAULT_CHARACTER
    frames = frames_for(name, "sleeping", stage="hatchling")
    assert frames == BABY[name]["sleeping"]


def test_frames_for_returns_adult_for_hatchling_missing_mood():
    """frames_for falls back to the adult sprite when baby art is unavailable.

    Uses alert, which has no baby art on purpose: alert/alarmed/offline carry a
    signal and stay full-size at every age. This test used to use perked, back
    when perked had no baby art either — but that was a bug rather than a
    decision, and it made a hatchling grow to adult size at the end of every turn.
    """
    name = DEFAULT_CHARACTER
    frames = frames_for(name, "alert", stage="hatchling")
    assert frames == CHARACTERS[name]["alert"]


def test_frames_for_returns_adult_for_juvenile():
    """frames_for returns adult sprites for juvenile stage."""
    name = DEFAULT_CHARACTER
    frames = frames_for(name, "sleeping", stage="juvenile")
    assert frames == CHARACTERS[name]["sleeping"]


def test_frames_for_returns_adult_by_default():
    """frames_for returns adult sprites by default (stage='adult')."""
    name = DEFAULT_CHARACTER
    frames = frames_for(name, "sleeping", stage="adult")
    assert frames == CHARACTERS[name]["sleeping"]


def test_frames_for_works_with_explicit_adult_stage():
    """frames_for explicitly with stage='adult' returns adult sprites."""
    name = DEFAULT_CHARACTER
    frames = frames_for(name, "sleeping", stage="adult")
    assert frames == CHARACTERS[name]["sleeping"]


def test_frames_for_defaults_to_adult_when_stage_omitted():
    """frames_for defaults to adult when stage parameter is omitted."""
    name = DEFAULT_CHARACTER
    frames_default = frames_for(name, "sleeping")
    frames_adult = frames_for(name, "sleeping", stage="adult")
    assert frames_default == frames_adult


# Tests for apply_petting()
def test_apply_petting_returns_happy_when_recently_petted():
    """apply_petting returns 'happy' when petted within duration."""
    petted_at = 100.0
    now = 105.0  # 5 seconds later, within 10-second duration
    result = apply_petting("sleeping", petted_at, now)
    assert result == "happy"


def test_apply_petting_returns_original_mood_when_not_petted():
    """apply_petting returns original mood when petted_at is None."""
    result = apply_petting("sleeping", None, 100.0)
    assert result == "sleeping"


def test_apply_petting_returns_original_mood_when_expired():
    """apply_petting returns original mood after petting expires."""
    petted_at = 100.0
    now = 111.0  # 11 seconds later, outside 10-second duration
    result = apply_petting("sleeping", petted_at, now)
    assert result == "sleeping"


def test_apply_petting_never_overrides_alert():
    """apply_petting never masks alert mood."""
    petted_at = 100.0
    now = 105.0  # Recently petted, but alert takes precedence
    result = apply_petting("alert", petted_at, now)
    assert result == "alert"


def test_apply_petting_never_overrides_alarmed():
    """apply_petting never masks alarmed mood."""
    petted_at = 100.0
    now = 105.0  # Recently petted, but alarmed takes precedence
    result = apply_petting("alarmed", petted_at, now)
    assert result == "alarmed"


def test_apply_petting_never_overrides_offline():
    """apply_petting never masks offline mood."""
    petted_at = 100.0
    now = 105.0  # Recently petted, but offline takes precedence
    result = apply_petting("offline", petted_at, now)
    assert result == "offline"


def test_apply_petting_at_duration_boundary():
    """apply_petting respects the duration boundary."""
    petted_at = 100.0
    duration = 10.0

    # Just before expiration: should show happy
    now_before = petted_at + (duration - 0.1)
    assert apply_petting("sleeping", petted_at, now_before) == "happy"

    # Just after expiration: should show original
    now_after = petted_at + duration + 0.1
    assert apply_petting("sleeping", petted_at, now_after) == "sleeping"


def test_apply_petting_is_pure():
    """apply_petting is deterministic with same inputs."""
    result1 = apply_petting("sleeping", 100.0, 105.0)
    result2 = apply_petting("sleeping", 100.0, 105.0)
    assert result1 == result2


# Tests for happy mood integration
def test_happy_mood_in_all_characters():
    """All characters must define happy mood."""
    for char_name in NAMES:
        assert "happy" in CHARACTERS[char_name], f"{char_name} missing happy mood"


def test_happy_mood_has_two_frames():
    """Happy mood should have exactly 2 frames for all characters."""
    for char_name in NAMES:
        frames = CHARACTERS[char_name]["happy"]
        assert len(frames) == 2, f"{char_name}/happy has {len(frames)} frames, expected 2"


def test_happy_in_compact_for_all_characters():
    """All characters must define happy in compact form."""
    for char_name in NAMES:
        assert "happy" in COMPACT[char_name], f"{char_name} missing happy in COMPACT"


def test_happy_compact_faces_within_budget():
    """Happy compact faces must fit column budget."""
    for char_name in NAMES:
        face = COMPACT[char_name]["happy"]
        w = width(face)
        assert w <= 8, f"{char_name}/happy compact is {w} columns: {face!r}"
