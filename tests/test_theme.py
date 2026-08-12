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
