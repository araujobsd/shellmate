import unicodedata

import pytest

from shellmate.theme import BOX, COLORS, GLYPHS, RESET


def test_both_glyph_sets_exist():
    assert set(GLYPHS) == {"unicode", "ascii"}
    assert set(BOX) == {"unicode", "ascii"}


@pytest.mark.parametrize("style", ["unicode", "ascii"])
def test_all_states_have_a_glyph(style):
    assert set(GLYPHS[style]) == {"idle", "working", "waiting", "blocked"}


@pytest.mark.parametrize("style", ["unicode", "ascii"])
def test_glyphs_and_box_share_one_east_asian_width_class(style):
    chars = list(GLYPHS[style].values()) + list(BOX[style].values())
    classes = {unicodedata.east_asian_width(c) for c in "".join(chars)}
    assert len(classes) == 1, f"{style} mixes width classes: {classes}"


def test_ascii_set_is_pure_ascii():
    joined = "".join(list(GLYPHS["ascii"].values()) + list(BOX["ascii"].values()))
    assert joined.isascii()


def test_every_state_glyph_is_distinct():
    for style in ("unicode", "ascii"):
        values = list(GLYPHS[style].values())
        assert len(set(values)) == len(values), f"{style} reuses a glyph"


def test_colors_cover_every_role():
    assert set(COLORS) == {"dim", "blue", "green", "yellow", "orange", "red"}


def test_colors_are_24bit_ansi():
    for name, esc in COLORS.items():
        assert esc.startswith("\033[38;2;"), name
        assert esc.endswith("m"), name


def test_reset_is_the_ansi_reset():
    assert RESET == "\033[0m"


def _rgb(code):
    """Pull (r, g, b) out of a 24-bit SGR sequence."""
    import re

    match = re.search(r"38;2;(\d+);(\d+);(\d+)", code)
    assert match, f"not a 24-bit colour: {code!r}"
    return tuple(int(part) for part in match.groups())


def test_every_species_has_a_colour():
    from shellmate.characters import NAMES
    from shellmate.theme import SPECIES_COLORS

    for species in NAMES:
        assert species in SPECIES_COLORS, f"{species} has no colour"


def test_species_colours_stay_clear_of_the_mood_marks():
    """A species colour must never blend into a mark painted next to it.

    The body wears the species colour and the trailing ! / !! / ? / z the mood
    colour, right beside each other. The first palette had the dog's tan equal to
    the yellow alert mark and the crab's red equal to the red alarmed mark, so the
    urgency marks disappeared into the body in the exact moods that needed them.
    """
    import math

    from shellmate.theme import COLORS, MARK_COLOR_ROLES, MIN_MARK_DISTANCE, SPECIES_COLORS

    for species, code in SPECIES_COLORS.items():
        for role in MARK_COLOR_ROLES:
            distance = math.dist(_rgb(code), _rgb(COLORS[role]))
            assert distance >= MIN_MARK_DISTANCE, (
                f"{species} is {distance:.0f} from the {role} mark colour "
                f"(needs {MIN_MARK_DISTANCE:.0f}); the mark would vanish into the body"
            )


def test_split_marks_never_loses_or_invents_characters():
    from shellmate.characters import BABY, CHARACTERS
    from shellmate.theme import split_marks

    for table in (CHARACTERS, BABY):
        for species, moods in table.items():
            for mood, frames in moods.items():
                for frame in frames:
                    for line in frame:
                        body, marks = split_marks(line)
                        assert body + marks == line, f"{species}/{mood}: {line!r}"


def test_split_marks_does_not_mistake_a_face_for_a_mark():
    """Eyes contain '.' and '*'-like glyphs; only a trailing run is a mark."""
    from shellmate.theme import split_marks

    assert split_marks("(o.o)") == ("(o.o)", "")
    assert split_marks("(-.-)z") == ("(-.-)", "z")
    assert split_marks("(-.-)..") == ("(-.-)", "..")
    assert split_marks("(O.O)!!") == ("(O.O)", "!!")
    assert split_marks(" >^<  ") == (" >^<  ", "")
