"""Tests for hatching and idle animation features."""

from shellmate.characters import (
    EGG,
    IDLE,
    NAMES,
    SPRITE_LINES,
    SPRITE_MAX_COLS,
    hatch_stage,
    idle_frame,
)
from shellmate.textwidth import width


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
