import pytest

from shellmate.textwidth import truncate, width


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("abc", 3),
        ("backend", 7),
        ("日本語", 6),  # each CJK ideograph is 2 columns
        ("weekly 🐎", 9),  # emoji is 2 columns
        ("ರ", 1),  # Kannada is 1 column despite being non-ASCII
    ],
)
def test_width_counts_display_columns(text, expected):
    assert width(text) == expected


def test_width_ignores_combining_marks():
    # e + combining acute occupies one column, not two
    assert width("é") == 1


@pytest.mark.parametrize(
    ("text", "budget"),
    [
        ("short", 20),
        ("plain-ascii-but-quite-long", 10),
        ("日本語のタブ名です", 10),
        ("🐎🐎🐎🐎🐎🐎🐎🐎", 9),
        ("日本語", 1),
    ],
)
def test_truncate_never_exceeds_budget(text, budget):
    assert width(truncate(text, budget)) <= budget


def test_truncate_leaves_short_text_untouched():
    assert truncate("backend", 20) == "backend"


def test_truncate_appends_ellipsis_when_cutting():
    assert truncate("plain-ascii-but-quite-long", 10).endswith("…")


def test_truncate_does_not_split_a_wide_glyph():
    # budget 5 cannot fit "🐎🐎" (4 cols) plus the ellipsis (1) and a third horse
    out = truncate("🐎🐎🐎", 5)
    assert width(out) <= 5
    assert out.endswith("…")


def test_width_and_truncate_use_same_character_widths():
    # Ensure width() and truncate() charge the same for each character when
    # cutting. Repeats each character class to force truncate's loop to execute.
    chars = ["a", "日", "🐎", "é", "╔"]  # ASCII, CJK, emoji, combining, ambiguous
    for ch in chars:
        # Repeat the character and set budget to force a cut, exercising truncate's
        # accumulation loop where _char_width() is called per character.
        s = ch * 6
        ch_width = width(ch)
        ellipsis_width = width("…")
        budget = ch_width * 3 + ellipsis_width  # allows 3 chars + ellipsis
        result = truncate(s, budget)
        # The result must fit the budget and stay under it. If truncate and width
        # charge differently for this character class, the result will exceed budget.
        assert width(result) <= budget, (
            f"truncate({ch!r}*6, budget={budget}) produced {result!r} with width {width(result)}"
        )
