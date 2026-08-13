"""Tests for hatching and idle animation features."""

import time

from shellmate.characters import (
    BABY,
    BABY_MOODS,
    CHARACTERS,
    EGG,
    EGG_COMPACT,
    IDLE,
    MAX_FRAMES,
    MOODS,
    NAMES,
    SPRITE_LINES,
    SPRITE_MAX_COLS,
    compact_for,
    egg_compact_for,
    frames_for,
    hatch_stage,
    idle_frame,
)
from shellmate.textwidth import width

# The moods that signal something needs you. These used to render full-size at
# every age; they now have hatchling art like every other mood, and the signal is
# carried by colour and the ! / !! marks instead.
SIGNAL_MOODS = ("alert", "alarmed", "offline")


def test_egg_exists():
    """EGG sequence is defined."""
    assert EGG is not None
    assert len(EGG) > 0


def test_egg_frames_structure():
    """Each egg frame has exactly 3 lines."""
    for i, frame in enumerate(EGG):
        assert len(frame) == SPRITE_LINES, (
            f"EGG[{i}] has {len(frame)} lines, expected {SPRITE_LINES}"
        )


def test_egg_frames_column_budget():
    """Each egg frame line is <= 12 columns."""
    for i, frame in enumerate(EGG):
        for j, line in enumerate(frame):
            w = width(line)
            assert w <= SPRITE_MAX_COLS, f"EGG[{i}][{j}] width {w} exceeds max {SPRITE_MAX_COLS}"


def test_idle_dict_exists():
    """IDLE dict is defined."""
    assert IDLE is not None
    assert isinstance(IDLE, dict)


def test_idle_covers_all_characters():
    """IDLE has entries for all characters."""
    for char_name in NAMES:
        assert char_name in IDLE, f"IDLE missing entry for {char_name}"


def test_idle_frames_structure():
    """Each idle frame has exactly 3 lines."""
    for char_name, variants in IDLE.items():
        assert isinstance(variants, list), f"IDLE[{char_name}] is not a list"
        for i, frame in enumerate(variants):
            assert len(frame) == SPRITE_LINES, f"IDLE[{char_name}][{i}] has {len(frame)} lines"


def test_idle_frames_column_budget():
    """Each idle frame line is <= 12 columns."""
    for char_name, variants in IDLE.items():
        for i, frame in enumerate(variants):
            for j, line in enumerate(frame):
                w = width(line)
                assert w <= SPRITE_MAX_COLS, f"IDLE[{char_name}][{i}][{j}] width {w} exceeds max"


def test_hatch_stage_returns_none_after_duration():
    """hatch_stage returns None when hatching is complete."""
    born_at = 1000.0
    duration = 8 * 3600  # 8 hours (default EGG_SECONDS)
    now = born_at + duration + 1.0  # Just after the duration
    result = hatch_stage(born_at, now, duration)
    assert result is None


def test_hatch_stage_returns_egg_indices_during_hatching():
    """hatch_stage returns valid egg frame indices while hatching."""
    born_at = 1000.0
    duration = 8 * 3600  # 8 hours

    for elapsed in [0.0, 1.0 * 3600, 2.0 * 3600, 4.0 * 3600, 7.99 * 3600]:
        now = born_at + elapsed
        result = hatch_stage(born_at, now, duration)
        assert result is not None
        assert isinstance(result, int)
        assert 0 <= result < len(EGG), f"Egg index {result} out of range [0, {len(EGG)})"


def test_hatch_stage_custom_duration():
    """hatch_stage respects custom duration parameter."""
    born_at = 1000.0
    duration = 3600.0  # 1 hour custom duration

    # At 59 minutes, should still be hatching
    result = hatch_stage(born_at, born_at + 59.0 * 60, duration)
    assert result is not None

    # At 61 minutes, should be hatched
    result = hatch_stage(born_at, born_at + 61.0 * 60, duration)
    assert result is None


def test_hatch_stage_is_pure():
    """hatch_stage is deterministic with same inputs."""
    born_at = 1000.0
    now = 1020.0
    result1 = hatch_stage(born_at, now, 8 * 3600)
    result2 = hatch_stage(born_at, now, 8 * 3600)
    assert result1 == result2


def test_hatch_stage_frames_cycle_across_8_hours():
    """Egg frames cycle across the full 8-hour duration."""
    born_at = 1000.0
    duration = 8 * 3600  # 8 hours
    frames_seen = set()

    # Sample egg frames throughout the 8-hour hatching period
    for hours_elapsed in range(0, 8):
        now = born_at + (hours_elapsed * 3600)
        result = hatch_stage(born_at, now, duration)
        if result is not None:
            frames_seen.add(result)

    # Should see multiple different frames across 8 hours
    assert len(frames_seen) > 1, f"Only saw {len(frames_seen)} unique frame(s) during hatching"
    # Should see frames near the end too
    now_near_end = born_at + (7.9 * 3600)
    result_near_end = hatch_stage(born_at, now_near_end, duration)
    assert result_near_end is not None, "Should still be hatching at 7.9 hours"


def test_idle_frame_returns_none_sometimes():
    """idle_frame returns None most of the time."""
    character = "cat"
    none_count = 0
    for tick in range(100):
        result = idle_frame(character, tick)
        if result is None:
            none_count += 1
    # Should return None much more often than not (every 17th tick)
    assert none_count > 80, f"idle_frame returned None {none_count}/100 times"


def test_idle_frame_returns_valid_frames():
    """idle_frame returns valid 3-line frames when not None."""
    character = "cat"
    for tick in range(0, 200, 17):  # Check every 17th tick
        result = idle_frame(character, tick)
        if result is not None:
            assert len(result) == SPRITE_LINES
            for line in result:
                assert width(line) <= SPRITE_MAX_COLS


def test_idle_frame_cycles_through_variants():
    """idle_frame cycles through different idle variants."""
    character = "cat"
    frames_seen = set()
    for tick in range(0, 1000, 17):  # Check every 17th tick
        result = idle_frame(character, tick)
        if result is not None:
            frames_seen.add(tuple(result))
    # Should see more than one variant
    assert len(frames_seen) > 1, f"Only saw {len(frames_seen)} idle variant(s)"


def test_idle_frame_is_pure():
    """idle_frame is deterministic with same inputs."""
    character = "cat"
    tick = 34  # Multiple of 17
    result1 = idle_frame(character, tick)
    result2 = idle_frame(character, tick)
    assert result1 == result2


def test_idle_frame_works_for_all_characters():
    """idle_frame works for all character types."""
    for character in NAMES:
        result = idle_frame(character, 17)
        # Should either return None or a valid frame
        if result is not None:
            assert len(result) == SPRITE_LINES


# --- compact surface must honour hatching -------------------------------------
# Regression: compact_for() originally took only (character, mood), so the --face
# surface skipped the egg entirely and a brand-new buddy showed its species face
# from second one. A macOS user reported "it's already a small owl" on a fresh
# install; the whole 8-hour hatch was invisible on that surface.


def test_compact_egg_has_one_frame_per_egg_frame():
    assert len(EGG_COMPACT) == len(EGG)


def test_compact_egg_frames_are_within_budget_and_ascii():
    for face in EGG_COMPACT:
        assert width(face) <= 8
        assert face.isascii()
        assert face.strip()


def test_compact_egg_frames_are_distinct():
    assert len(set(EGG_COMPACT)) == len(EGG_COMPACT)


def test_egg_compact_for_clamps_out_of_range():
    assert egg_compact_for(-5) == EGG_COMPACT[0]
    assert egg_compact_for(999) == EGG_COMPACT[-1]


def test_compact_for_shows_egg_before_hatching():
    now = time.time()
    assert compact_for("owl", "working", born_at=now, now=now) in EGG_COMPACT
    assert compact_for("owl", "working", born_at=now - 3600, now=now) in EGG_COMPACT


def test_compact_for_shows_species_after_hatching():
    now = time.time()
    face = compact_for("owl", "working", born_at=now - 9 * 3600, now=now)
    assert face not in EGG_COMPACT
    assert face == "{o.o}"


def test_compact_for_without_birth_info_is_unchanged():
    # Callers that cannot supply birth info keep the old behaviour rather than
    # guessing — never show an egg for a buddy whose age we do not know.
    assert compact_for("owl", "working") == "{o.o}"


def test_baby_covers_every_baby_mood_for_every_species():
    """Every species needs hatchling art for every mood listed in BABY_MOODS.

    A mood missing here does not raise — frames_for silently falls back to the
    adult sprite, so the only symptom is the buddy changing size on screen.
    """
    for species in NAMES:
        assert species in BABY, f"{species} has no hatchling art at all"
        for mood in BABY_MOODS:
            assert mood in BABY[species], f"{species} is missing hatchling {mood}"
            frames = BABY[species][mood]
            if mood == "offline":
                assert len(frames) == 1, f"{species}/offline must not animate"
            else:
                assert 2 <= len(frames) <= MAX_FRAMES, f"{species}/{mood} has {len(frames)} frames"
            for i, frame in enumerate(frames):
                assert len(frame) == SPRITE_LINES, f"{species}/{mood} f{i} line count"
                for line in frame:
                    assert width(line) <= SPRITE_MAX_COLS, f"{species}/{mood} f{i}: {line!r}"


def test_hatchling_does_not_grow_up_on_perked_or_happy():
    """The bug this pins: a hatchling jumped to full adult size when perked.

    perked fires at the end of every turn and happy on every pet, so the buddy
    visibly grew up and shrank back over and over during normal use.
    """
    for species in NAMES:
        for mood in BABY_MOODS:
            got = frames_for(species, mood, stage="hatchling")
            assert got == BABY[species][mood], f"{species}/{mood} is not the baby sprite"
            assert got != CHARACTERS[species][mood], f"{species}/{mood} fell back to adult"


def test_a_hatchling_is_hatchling_sized_in_every_mood():
    """No mood may render a hatchling at adult size — including the signal moods.

    alert/alarmed/offline used to be excluded so they would stay "legible" at full
    size. But an idle solo session sits in alert, so the buddy was adult-sized
    most of the time and a hatchling only while a prompt ran; the size flipped
    constantly and the stage was nearly invisible. Urgency now rides entirely on
    colour and the ! / !! marks, which do not depend on size.
    """
    for species in NAMES:
        for mood in SIGNAL_MOODS:
            assert mood in BABY_MOODS, f"{mood} lost its hatchling art"
        for mood in MOODS:
            got = frames_for(species, mood, stage="hatchling")
            assert got == BABY[species][mood], f"{species}/{mood} is not the baby sprite"
            assert got != CHARACTERS[species][mood], f"{species}/{mood} fell back to adult"


def _all_art_lines():
    """Yield (label, line) for every sprite line in every art table."""
    for table_name, table in (("BABY", BABY), ("CHARACTERS", CHARACTERS)):
        for species, moods in table.items():
            for mood, frames in moods.items():
                for i, frame in enumerate(frames):
                    for line in frame:
                        yield f"{table_name}[{species}][{mood}] f{i}", line
    for i, frame in enumerate(EGG):
        for line in frame:
            yield f"EGG f{i}", line
    for species, frames in IDLE.items():
        for i, frame in enumerate(frames):
            for line in frame:
                yield f"IDLE[{species}] f{i}", line


def test_sprite_art_has_no_escape_artifacts():
    r"""A raw string does not process escapes, so r"\_\\" keeps every backslash.

    Two sprites shipped this way: the baby owl's feet, written r"-\"-\"-", showed
    as -\"-\"- instead of -"-"-; and the last egg frame, written r"  \\_/\\  ",
    showed as \\_/\\. Both are invisible in the source and obvious on screen.
    """
    for label, line in _all_art_lines():
        assert '\\"' not in line, f'{label}: {line!r} contains \\"'
        assert "\\\\" not in line, f"{label}: {line!r} contains a doubled backslash"


def test_baby_keeps_its_adult_mirror_pairs_balanced():
    r"""A limb lost in the shrink shows up as an unbalanced mirror pair.

    The cat shipped as /\_\ where the adult is /\_/\ — one ear short. Character-set
    checks miss it, because both / and \ are still present; only the counts differ.
    """
    pairs = [("/", "\\"), ("<", ">"), ("(", ")"), ("[", "]")]
    for species in NAMES:
        for mood in BABY_MOODS:
            baby_frames = BABY[species][mood]
            adult_frames = CHARACTERS[species][mood]
            for i, (baby, adult) in enumerate(zip(baby_frames, adult_frames, strict=True)):
                for line_no, (baby_line, adult_line) in enumerate(zip(baby, adult, strict=True)):
                    for left, right in pairs:
                        if adult_line.count(left) != adult_line.count(right):
                            continue  # adult is deliberately lopsided here
                        assert baby_line.count(left) == baby_line.count(right), (
                            f"{species}/{mood} f{i} line{line_no}: adult {adult_line!r} balances "
                            f"{left}{right} but baby {baby_line!r} does not"
                        )
