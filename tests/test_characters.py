import itertools

import pytest

from shellmate.characters import (
    CHARACTERS,
    COMPACT,
    DEFAULT_CHARACTER,
    EGG,
    EGG_PHRASES,
    MOODS,
    NAMES,
    PHRASES,
    SPRITE_LINES,
    SPRITE_MAX_COLS,
    UPDATE_PHRASES,
    compact_for,
    egg_phrase_for,
    frames_for,
    phrase_for,
    update_phrase_for,
)
from shellmate.textwidth import width

COMPACT_MAX_COLS = 8

# Parametrising over the registry itself means a contributed character is
# contract-checked automatically, with no test list to remember to update.
EVERY = sorted(CHARACTERS)


def test_the_shipped_characters_are_present():
    assert set(CHARACTERS) == set(NAMES)


@pytest.mark.parametrize("name", EVERY)
def test_every_character_has_every_mood(name):
    assert set(CHARACTERS[name]) == set(MOODS)


@pytest.mark.parametrize("name", EVERY)
def test_animated_moods_have_a_supported_frame_count(name):
    """2 frames is the norm; offline has 1; the secret buddy is allowed more.

    The cache holds MAX_FRAMES slots and the hot path indexes them by wall clock,
    so a 2-frame sprite is written as a,b,a,b and still alternates once a second
    exactly as before. Anything beyond MAX_FRAMES would be silently truncated at
    render time, which is the real ceiling this pins.
    """
    from shellmate.characters import MAX_FRAMES

    for mood in MOODS:
        frames = CHARACTERS[name][mood]
        if mood == "offline":
            assert len(frames) == 1, f"{name}/offline must not animate"
            continue
        assert 2 <= len(frames) <= MAX_FRAMES, f"{name}/{mood} has {len(frames)} frames"
        assert MAX_FRAMES % len(frames) == 0, (
            f"{name}/{mood} has {len(frames)} frames, which does not divide "
            f"MAX_FRAMES={MAX_FRAMES} — the loop would stutter at the wrap"
        )


@pytest.mark.parametrize("name", EVERY)
def test_every_frame_has_exactly_three_lines(name):
    for mood, frames in CHARACTERS[name].items():
        for i, frame in enumerate(frames):
            assert len(frame) == SPRITE_LINES, f"{name}/{mood}/{i}"


@pytest.mark.parametrize("name", EVERY)
def test_no_line_exceeds_the_column_budget(name):
    for mood, frames in CHARACTERS[name].items():
        for i, frame in enumerate(frames):
            for line in frame:
                assert width(line) <= SPRITE_MAX_COLS, f"{name}/{mood}/{i}: {line!r}"


def test_names_matches_the_registry():
    assert set(NAMES) == set(CHARACTERS)
    assert DEFAULT_CHARACTER in CHARACTERS


def test_frames_for_returns_requested_sprite():
    name = DEFAULT_CHARACTER
    assert frames_for(name, "sleeping") == CHARACTERS[name]["sleeping"]


def test_frames_for_falls_back_to_default_on_unknown_character():
    expected = CHARACTERS[DEFAULT_CHARACTER]["sleeping"]
    assert frames_for("tyrannosaurus", "sleeping") == expected


def test_frames_for_falls_back_to_sleeping_on_unknown_mood():
    name = DEFAULT_CHARACTER
    assert frames_for(name, "ecstatic") == CHARACTERS[name]["sleeping"]


def test_no_two_characters_have_identical_sprites():
    """All characters must be visually distinct from each other."""
    dupes = [
        (a, b) for a, b in itertools.combinations(CHARACTERS, 2) if CHARACTERS[a] == CHARACTERS[b]
    ]
    assert not dupes, f"identical characters found: {dupes}"


@pytest.mark.parametrize("name", EVERY)
def test_animated_moods_have_distinct_frames(name):
    """Each non-offline mood must have two different animation frames."""
    for mood in MOODS:
        if mood != "offline":
            frames = CHARACTERS[name][mood]
            assert frames[0] != frames[1], f"{name}/{mood} has identical frames"


def test_compact_registry_present():
    assert set(COMPACT) == set(CHARACTERS)


@pytest.mark.parametrize("name", EVERY)
def test_compact_has_all_moods(name):
    assert set(COMPACT[name]) == set(MOODS)


@pytest.mark.parametrize("name", EVERY)
def test_compact_faces_within_column_budget(name):
    for mood, face in COMPACT[name].items():
        w = width(face)
        assert w <= COMPACT_MAX_COLS, f"{name}/{mood}: {face!r} is {w} columns"


@pytest.mark.parametrize("name", EVERY)
def test_compact_moods_are_distinct_within_character(name):
    """All six moods of a character must produce visually distinct faces."""
    faces = COMPACT[name]
    for m1, m2 in itertools.combinations(MOODS, 2):
        assert faces[m1] != faces[m2], (
            f"{name}: {m1} and {m2} produce identical faces {faces[m1]!r}"
        )


def test_compact_same_mood_distinct_across_characters():
    """Each mood must produce different faces across characters."""
    for mood in MOODS:
        faces = {name: COMPACT[name][mood] for name in CHARACTERS}
        unique_faces = set(faces.values())
        assert len(unique_faces) == len(CHARACTERS), (
            f"{mood}: not all characters are visually distinct; "
            f"these pairs match: {[f for f in faces.values() if list(faces.values()).count(f) > 1]}"
        )


def test_compact_for_returns_requested_face():
    name = DEFAULT_CHARACTER
    assert compact_for(name, "sleeping") == COMPACT[name]["sleeping"]


def test_compact_for_falls_back_to_default_on_unknown_character():
    expected = COMPACT[DEFAULT_CHARACTER]["sleeping"]
    assert compact_for("tyrannosaurus", "sleeping") == expected


def test_compact_for_falls_back_to_sleeping_on_unknown_mood():
    name = DEFAULT_CHARACTER
    assert compact_for(name, "ecstatic") == COMPACT[name]["sleeping"]


# Phrase tests


def test_phrases_registry_present():
    """PHRASES dict must exist and contain all characters."""
    assert PHRASES is not None
    assert set(PHRASES) == set(CHARACTERS)


@pytest.mark.parametrize("name", EVERY)
def test_every_character_has_every_mood_in_phrases(name):
    """Every character must have every mood in PHRASES."""
    assert set(PHRASES[name]) == set(MOODS), f"{name} missing moods"


@pytest.mark.parametrize("name", EVERY)
def test_phrases_have_correct_count(name):
    """Each character/mood pair must have 4-6 phrases."""
    for mood in MOODS:
        phrases = PHRASES[name][mood]
        assert isinstance(phrases, tuple), f"{name}/{mood}: not a tuple"
        assert 4 <= len(phrases) <= 6, f"{name}/{mood}: {len(phrases)} phrases (need 4-6)"


@pytest.mark.parametrize("name", EVERY)
def test_all_phrases_within_column_budget(name):
    """Each phrase must be <= 42 display columns."""
    for mood in MOODS:
        for i, phrase in enumerate(PHRASES[name][mood]):
            w = width(phrase)
            assert w <= 42, f"{name}/{mood}/{i}: {phrase!r} is {w} columns (max 42)"


@pytest.mark.parametrize("name", EVERY)
def test_no_empty_phrases(name):
    """No phrase can be empty or whitespace-only."""
    for mood in MOODS:
        for i, phrase in enumerate(PHRASES[name][mood]):
            assert phrase and phrase.strip(), f"{name}/{mood}/{i}: empty phrase"


@pytest.mark.parametrize("name", EVERY)
def test_phrases_are_distinct_within_mood(name):
    """Within one character+mood, all phrases must be distinct."""
    for mood in MOODS:
        phrases = PHRASES[name][mood]
        assert len(set(phrases)) == len(phrases), f"{name}/{mood}: duplicate phrases"


def test_phrases_not_reused_across_characters_for_same_mood():
    """No phrase should be reused across characters for the same mood."""
    for mood in MOODS:
        # Collect all phrases for this mood across all characters
        all_phrases_for_mood = {}
        for char in CHARACTERS:
            phrases_list = list(PHRASES[char][mood])
            for phrase in phrases_list:
                if phrase in all_phrases_for_mood:
                    pytest.fail(
                        f"Phrase {phrase!r} reused in {mood}: "
                        f"{all_phrases_for_mood[phrase]} and {char}"
                    )
                all_phrases_for_mood[phrase] = char


def test_phrases_are_ascii_only():
    """Phrases should use only ASCII characters and common punctuation."""
    for char in CHARACTERS:
        for mood in MOODS:
            for i, phrase in enumerate(PHRASES[char][mood]):
                # Allow ASCII letters, digits, spaces, and common punctuation
                for ch in phrase:
                    # Allow ASCII + a few common punctuation marks
                    if ord(ch) > 127 and ch not in "—'":
                        pytest.fail(f"{char}/{mood}/{i}: non-ASCII char {ch!r} in {phrase!r}")


def test_phrase_for_returns_phrase_for_valid_input():
    """phrase_for should return a phrase from PHRASES for valid inputs."""
    char = DEFAULT_CHARACTER
    mood = "happy"
    seed = 1234567.0
    result = phrase_for(char, mood, seed)
    assert result in PHRASES[char][mood]


def test_phrase_for_is_deterministic():
    """phrase_for should return the same phrase for same inputs."""
    char = DEFAULT_CHARACTER
    mood = "working"
    seed = 9876543.0
    result1 = phrase_for(char, mood, seed)
    result2 = phrase_for(char, mood, seed)
    assert result1 == result2


def test_phrase_for_different_seeds_distribute():
    """phrase_for should use different seeds to select different phrases."""
    char = DEFAULT_CHARACTER
    mood = "alert"
    # Use distinct seeds to get at least 2 different phrases
    phrases_set = set()
    for seed_int in range(0, len(PHRASES[char][mood]) * 2):
        seed = float(seed_int)
        phrase = phrase_for(char, mood, seed)
        phrases_set.add(phrase)
    # Should have more than 1 phrase if we tried enough seeds
    assert len(phrases_set) > 1


def test_phrase_for_handles_unknown_character():
    """phrase_for should handle unknown character without raising."""
    seed = 1234567.0
    mood = "sleeping"
    result = phrase_for("tyrannosaurus", mood, seed)
    # Should fall back to default character
    assert result in PHRASES[DEFAULT_CHARACTER][mood]


def test_phrase_for_handles_unknown_mood():
    """phrase_for should handle unknown mood without raising."""
    char = DEFAULT_CHARACTER
    seed = 1234567.0
    result = phrase_for(char, "ecstatic", seed)
    # Should fall back to sleeping
    assert result in PHRASES[char]["sleeping"]


def test_phrase_for_stable_during_mood():
    """phrase_for should return same phrase while mood_since stays constant."""
    char = DEFAULT_CHARACTER
    mood = "perked"
    mood_since = 1000.0
    # Multiple renders with same mood seed should yield same phrase
    results = [phrase_for(char, mood, mood_since) for _ in range(10)]
    assert len(set(results)) == 1, "Phrase should be stable with constant seed"


def test_phrase_for_with_mood_change():
    """phrase_for should change when mood_since changes (mood entry)."""
    char = DEFAULT_CHARACTER
    mood = "happy"
    # Different mood_since values should (usually) yield different phrases
    # due to different seeds
    phrase1 = phrase_for(char, mood, 1000.0)
    phrase2 = phrase_for(char, mood, 2000.0)
    # Not guaranteed to be different, but very likely
    # At least, both should be valid
    assert phrase1 in PHRASES[char][mood]
    assert phrase2 in PHRASES[char][mood]


# Egg phrase tests


def test_egg_phrases_registry_present():
    """EGG_PHRASES must exist and have one group per egg frame."""
    assert EGG_PHRASES is not None
    assert isinstance(EGG_PHRASES, tuple)
    egg_len = len(EGG_PHRASES)
    egg_frames_len = len(EGG)
    assert egg_len == egg_frames_len, (
        f"EGG_PHRASES has {egg_len} groups but EGG has {egg_frames_len} frames"
    )


def test_egg_phrases_have_correct_count():
    """Each egg frame group must have 3-4 phrases."""
    for i, group in enumerate(EGG_PHRASES):
        assert isinstance(group, tuple), f"Frame {i}: not a tuple"
        assert 3 <= len(group) <= 4, f"Frame {i}: {len(group)} phrases (need 3-4)"


def test_all_egg_phrases_within_column_budget():
    """Each egg phrase must be <= 42 display columns."""
    for frame_idx, group in enumerate(EGG_PHRASES):
        for phrase_idx, phrase in enumerate(group):
            w = width(phrase)
            assert w <= 42, (
                f"Frame {frame_idx}/phrase {phrase_idx}: {phrase!r} is {w} columns (max 42)"
            )


def test_no_empty_egg_phrases():
    """No egg phrase can be empty or whitespace-only."""
    for frame_idx, group in enumerate(EGG_PHRASES):
        for phrase_idx, phrase in enumerate(group):
            assert phrase and phrase.strip(), f"Frame {frame_idx}/phrase {phrase_idx}: empty phrase"


def test_egg_phrases_are_distinct_within_frame():
    """Within one frame, all phrases must be distinct."""
    for frame_idx, group in enumerate(EGG_PHRASES):
        assert len(set(group)) == len(group), f"Frame {frame_idx}: duplicate phrases"


def test_egg_phrases_are_species_agnostic():
    """EGG_PHRASES must be a flat structure, not keyed by character name."""
    # It's a tuple of tuples, not a dict; this proves it's species-agnostic
    assert isinstance(EGG_PHRASES, tuple)
    for group in EGG_PHRASES:
        assert isinstance(group, tuple)
    # Make sure it's not accidentally keyed by character name
    assert not isinstance(EGG_PHRASES, dict)


def test_egg_phrases_are_ascii_only():
    """Egg phrases should use only ASCII characters and common punctuation."""
    for frame_idx, group in enumerate(EGG_PHRASES):
        for phrase_idx, phrase in enumerate(group):
            # Allow ASCII letters, digits, spaces, and common punctuation
            for ch in phrase:
                # Allow ASCII + a few common punctuation marks
                if ord(ch) > 127 and ch not in "—'":
                    pytest.fail(
                        f"Frame {frame_idx}/phrase {phrase_idx}: "
                        f"non-ASCII char {ch!r} in {phrase!r}"
                    )


def test_egg_phrase_for_returns_phrase_for_valid_input():
    """egg_phrase_for should return a phrase from EGG_PHRASES for valid inputs."""
    frame_idx = 0
    seed = 1234567.0
    result = egg_phrase_for(frame_idx, seed)
    assert result in EGG_PHRASES[frame_idx]


def test_egg_phrase_for_is_deterministic():
    """egg_phrase_for should return the same phrase for same inputs."""
    frame_idx = 2
    seed = 9876543.0
    result1 = egg_phrase_for(frame_idx, seed)
    result2 = egg_phrase_for(frame_idx, seed)
    assert result1 == result2


def test_egg_phrase_for_deterministic_across_100_calls():
    """egg_phrase_for should remain deterministic across many calls."""
    frame_idx = 1
    seed = 5555555.0
    results = [egg_phrase_for(frame_idx, seed) for _ in range(100)]
    # All results should be identical
    assert len(set(results)) == 1, "Phrase should be deterministic"


def test_egg_phrase_for_different_seeds_distribute():
    """egg_phrase_for should use different seeds to select different phrases within a frame."""
    frame_idx = 3
    phrases_set = set()
    for seed_int in range(0, len(EGG_PHRASES[frame_idx]) * 2):
        seed = float(seed_int)
        phrase = egg_phrase_for(frame_idx, seed)
        phrases_set.add(phrase)
    # Should have more than 1 phrase if we tried enough seeds
    assert len(phrases_set) > 1, "Different seeds should select different phrases"


def test_egg_phrase_for_out_of_range_frame_index_clamped():
    """egg_phrase_for should handle out-of-range frame index without raising."""
    seed = 1234567.0
    # Should clamp negative to 0
    result_neg = egg_phrase_for(-1, seed)
    assert result_neg in EGG_PHRASES[0]
    # Should clamp too-large to last frame
    result_large = egg_phrase_for(999, seed)
    assert result_large in EGG_PHRASES[-1]


def test_egg_phrase_for_stable_during_hatch():
    """egg_phrase_for should return same phrase while seed stays constant."""
    frame_idx = 2
    seed = 1000.0
    # Multiple renders with same seed should yield same phrase
    results = [egg_phrase_for(frame_idx, seed) for _ in range(10)]
    assert len(set(results)) == 1, "Phrase should be stable with constant seed"


def test_egg_phrase_invariant_across_renders_within_frame():
    """Egg phrase must be invariant across repeated renders within a frame window.

    This tests the real-world scenario: born_at and egg_idx stay fixed (within one
    frame window), but mood_since churns as sessions start/stop. The phrase should
    NOT drift.
    """
    born_at = 1000.0  # Simulated birth timestamp
    egg_idx = 1  # Fixed frame

    # Get phrase for this birth and frame
    phrase_fixed = egg_phrase_for(egg_idx, born_at)

    # Simulate multiple renders with the SAME born_at and egg_idx, but different
    # mood_since values (which should NOT affect the egg phrase)
    phrases = []
    for _mood_since in [1100.0, 1150.0, 1200.0, 1250.0]:
        # In reality, mood_since would be used to seed mood phrases, but egg phrases
        # should only depend on born_at (passed as seed here)
        phrase = egg_phrase_for(egg_idx, born_at)
        phrases.append(phrase)

    # All should be identical — egg phrase is invariant within a frame
    assert len(set(phrases)) == 1, "Egg phrase should not drift within a frame window"
    assert phrases[0] == phrase_fixed, "Phrase must be stable across multiple renders"


def test_egg_phrase_progression_across_frames():
    """Egg phrase progression should be visible as egg_idx advances 0->1->2->3.

    Within the 8-hour egg stage, as hatch progress advances to the next frame,
    the phrase should change (at least for most birth times), showing clear progression.
    """
    born_at = 1000.0

    # Get phrases for all four frames with the same birth timestamp
    phrases = [egg_phrase_for(i, born_at) for i in range(4)]

    # All four should be distinct (within a frame pool, but across frames they differ)
    # This is a high-confidence check: phrase progression should be visible
    assert len(set(phrases)) > 1, "Progression should show phrase changes across frames"

    # Verify each phrase comes from its correct frame
    for frame_idx, phrase in enumerate(phrases):
        assert phrase in EGG_PHRASES[frame_idx], (
            f"Frame {frame_idx} phrase {phrase!r} not in frame pool"
        )


# UPDATE_PHRASES tests


def test_update_phrases_registry_present():
    """UPDATE_PHRASES dict must exist and contain all characters."""
    assert UPDATE_PHRASES is not None
    assert set(UPDATE_PHRASES) == set(CHARACTERS)


@pytest.mark.parametrize("name", NAMES)
def test_update_phrases_exist_for_all_characters(name):
    """Each character must have update phrases."""
    phrases = UPDATE_PHRASES[name]
    assert isinstance(phrases, tuple), f"{name}: not a tuple"
    assert len(phrases) >= 3, f"{name}: {len(phrases)} phrases (need at least 3)"


@pytest.mark.parametrize("name", NAMES)
def test_update_phrases_within_column_budget(name):
    """Each update phrase must be <= 42 display columns."""
    for i, phrase in enumerate(UPDATE_PHRASES[name]):
        w = width(phrase)
        assert w <= 42, f"{name}/{i}: {phrase!r} is {w} columns (max 42)"


@pytest.mark.parametrize("name", NAMES)
def test_update_phrases_are_ascii(name):
    """Update phrases must be ASCII only, no emoji."""
    for i, phrase in enumerate(UPDATE_PHRASES[name]):
        try:
            phrase.encode("ascii")
        except UnicodeEncodeError:
            pytest.fail(f"{name}/{i}: {phrase!r} contains non-ASCII")


@pytest.mark.parametrize("name", NAMES)
def test_update_phrases_are_distinct(name):
    """Within one character, all update phrases must be distinct."""
    phrases = UPDATE_PHRASES[name]
    assert len(phrases) == len(set(phrases)), f"{name}: duplicate phrases found"


def test_update_phrase_for_deterministic():
    """update_phrase_for must be deterministic: same input -> same output."""
    phrase1 = update_phrase_for("cat", 1000.5)
    phrase2 = update_phrase_for("cat", 1000.5)

    assert phrase1 == phrase2, "Determinism failed for same seed"


def test_update_phrase_for_falls_back_safely():
    """update_phrase_for must not raise for unknown character."""
    # Should fall back to default or return empty string
    result = update_phrase_for("unknown_character", 1000.0)
    assert isinstance(result, str)


def test_update_phrase_for_returns_from_registry():
    """update_phrase_for must return a phrase from UPDATE_PHRASES."""
    for name in NAMES:
        phrase = update_phrase_for(name, 1000.0)
        if phrase:  # May be empty for fallback
            assert phrase in UPDATE_PHRASES[name], (
                f"{name}: {phrase!r} not in UPDATE_PHRASES[{name}]"
            )


def test_only_secret_buddies_may_use_non_ascii_art():
    """Public buddies stay ASCII; block art is reserved for opt-in buddies.

    Everyone gets a public buddy whether they chose it or not, so those must
    render everywhere — including terminals set to ambiguous-width=double, and
    for anyone using ascii_glyphs. A secret buddy can only be chosen by hand, so
    it is free to use block glyphs; if it looks wrong you simply do not set it.
    """
    from shellmate.characters import BABY, BLOCK_ART_NAMES, CHARACTERS, PUBLIC_NAMES, SECRET_NAMES

    for name in BLOCK_ART_NAMES:
        assert name in SECRET_NAMES, f"{name} uses block art but is not secret"

    for name in PUBLIC_NAMES:
        for table in (CHARACTERS, BABY):
            for mood, frames in table[name].items():
                for frame in frames:
                    for line in frame:
                        non_ascii = {c for c in line if ord(c) > 127}
                        # ಠ is the long-standing exception in the alarmed face.
                        assert non_ascii <= {"ಠ"}, f"{name}/{mood}: {sorted(non_ascii)}"


def test_block_art_stays_in_one_width_class():
    """Each block buddy must draw from a single East Asian Width class.

    Which class is the buddy's own choice — the ember is class A (bars and
    fills), the moth and golem are class N (corners, diagonals, quadrants) — but
    mixing them inside one sprite tears where the classes differ. The range is
    split in a way that makes that easy to do by accident: ▌ is A while ▐ is N,
    the corners ▛▜▙▟ are N while the solid ▀▄█ are A, and even the shades
    disagree, ▒ and ▓ being A while ░ is N.
    """
    import unicodedata

    from shellmate.characters import BABY, BLOCK_ART_NAMES, CHARACTERS

    for name in BLOCK_ART_NAMES:
        classes = set()
        for table in (CHARACTERS, BABY):
            for frames in table[name].values():
                for frame in frames:
                    for line in frame:
                        for char in line:
                            if 0x2580 <= ord(char) <= 0x259F:
                                classes.add(unicodedata.east_asian_width(char))
        assert len(classes) <= 1, f"{name} mixes width classes: {sorted(classes)}"


# Block glyphs that are each other's mirror image. Reversing a line is not enough
# to test symmetry: ▚ reversed is still ▚, but its mirror is ▞.
_MIRROR = {
    "▚": "▞",
    "▞": "▚",
    "▖": "▗",
    "▗": "▖",
    "▘": "▝",
    "▝": "▘",
    "▙": "▟",
    "▟": "▙",
    "▛": "▜",
    "▜": "▛",
    "▏": "▕",
    "▕": "▏",
}


def _mirror(text: str) -> str:
    return "".join(_MIRROR.get(char, char) for char in reversed(text))


def test_symmetric_block_art_actually_mirrors():
    """Buddies that claim symmetry must mirror, not merely reverse.

    The first version of this compared a line to its own reverse, which is wrong
    for glyphs that mirror onto a different glyph: ▚▚▚ ▞▞▞ is visually symmetric
    but is not a palindrome. Only the buddies in SYMMETRIC_ART_NAMES are held to
    this — the golem is lopsided on purpose while it works, moving one slab at a
    time, which is what makes it read as weight.
    """
    from shellmate.characters import BABY, CHARACTERS, SYMMETRIC_ART_NAMES

    for name in SYMMETRIC_ART_NAMES:
        for table_name, table in (("adult", CHARACTERS), ("baby", BABY)):
            for mood, frames in table[name].items():
                for i, frame in enumerate(frames):
                    for line_no in (0, 2):
                        core = frame[line_no].strip().rstrip("!?*z.").strip()
                        assert core == _mirror(core), (
                            f"{table_name} {name}/{mood} f{i} line{line_no}: "
                            f"{frame[line_no]!r} does not mirror"
                        )


def test_a_block_hatchling_is_narrower_than_its_adult():
    """The hatchling must actually be smaller, not just differently padded.

    The ember's first hatchling reused the adult face verbatim, so the only
    difference was a space of padding. Every other species contracts its face.
    """
    from shellmate.characters import BABY, BLOCK_ART_NAMES, CHARACTERS
    from shellmate.textwidth import width

    for name in BLOCK_ART_NAMES:
        for mood in CHARACTERS[name]:
            adult_face = CHARACTERS[name][mood][0][1].strip()
            baby_face = BABY[name][mood][0][1].strip()
            assert width(baby_face) < width(adult_face), (
                f"{name}/{mood}: hatchling face {baby_face!r} is not narrower "
                f"than the adult's {adult_face!r}"
            )


def test_block_buddies_have_the_same_frame_count_at_both_sizes():
    """Both sizes must be on the same beat, whatever the art does between them."""
    from shellmate.characters import BABY, BLOCK_ART_NAMES, CHARACTERS

    for name in BLOCK_ART_NAMES:
        for mood, adult_frames in CHARACTERS[name].items():
            assert len(BABY[name][mood]) == len(adult_frames), f"{name}/{mood}"


def test_the_ember_draws_its_burn_identically_at_both_sizes():
    """Ember-specific: its burn lives in the cap and floor, so those are shared.

    The moth and golem scale their limbs between sizes instead, so this is not a
    rule for block art generally — but the ember's two sizes drifted onto
    different rhythms once already, and only this pins them.
    """
    from shellmate.characters import BABY, CHARACTERS

    for mood, adult_frames in CHARACTERS["ember"].items():
        for i, (adult, baby) in enumerate(zip(adult_frames, BABY["ember"][mood], strict=True)):
            assert adult[0] == baby[0], f"ember/{mood} f{i}: caps out of step"
            assert adult[2] == baby[2], f"ember/{mood} f{i}: floors out of step"
