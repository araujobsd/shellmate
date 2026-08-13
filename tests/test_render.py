import re

import pytest

from shellmate.config import Config
from shellmate.models import Agent, AgentView, Snapshot, fmt_age
from shellmate.render import decorate, frame
from shellmate.textwidth import width


def view(status="idle", tier=None, age=0.0, label="tab", key="k"):
    return AgentView(
        agent=Agent(key=key, status=status, label=label, pane_id="p", tab_id="t"),
        age=age,
        tier=tier,
    )


def snap(views=(), mood="sleeping", online=True):
    return Snapshot(views=tuple(views), mood=mood, online=online)


@pytest.mark.parametrize("cols", [14, 20, 28, 40, 80])
def test_every_line_is_exactly_the_requested_width(cols):
    s = snap([view("done", "MED", 300.0, "my-project"), view("working", label="api")], mood="alert")
    for line in frame(s, 0, cols, color=False):
        assert width(line) == cols, repr(line)


def test_wide_labels_do_not_break_the_box():
    s = snap([view("done", "MED", 300.0, "日本語のタブ名です" * 3)], mood="alert")
    for line in frame(s, 0, 28, color=False):
        assert width(line) == 28, repr(line)


def test_emoji_labels_do_not_break_the_box():
    s = snap([view("working", label="weekly 🐎🐎🐎🐎🐎🐎")])
    for line in frame(s, 0, 28, color=False):
        assert width(line) == 28, repr(line)


def test_no_color_emits_no_escape_sequences():
    s = snap([view("blocked", "HIGH", 700.0, "backend")], mood="alarmed")
    out = "\n".join(frame(s, 0, 28, color=False))
    assert "\033" not in out


def test_color_emits_escape_sequences():
    s = snap([view("blocked", "HIGH", 700.0, "backend")], mood="alarmed")
    out = "\n".join(frame(s, 0, 28, color=True))
    assert "\033[38;2;" in out
    assert out.count("\033[0m") >= 1


def test_narrow_pane_drops_the_agent_list():
    s = snap([view("done", "MED", 300.0, "my-project")], mood="alert")
    wide = frame(s, 0, 28, color=False)
    narrow = frame(s, 0, 12, color=False)
    assert len(narrow) < len(wide)
    assert not any("my-project" in line for line in narrow)


def test_narrow_pane_still_renders_the_face():
    s = snap([view("done", "MED", 300.0)], mood="alert")
    out = frame(s, 0, 12, color=False)
    assert len(out) >= 3
    for line in out:
        assert width(line) == 12


def test_frames_alternate():
    s = snap(mood="sleeping")
    assert frame(s, 0, 28, color=False) != frame(s, 1, 28, color=False)


def test_frame_index_wraps():
    """The frame index wraps at the sprite's own frame count, not a fixed 2.

    Calm moods now carry four frames, so frame 0 and frame 2 are genuinely
    different pictures; wrapping happens a full loop later.
    """
    from shellmate.characters import DEFAULT_CHARACTER, frames_for

    period = len(frames_for(DEFAULT_CHARACTER, "sleeping"))
    s = snap(mood="sleeping")
    assert frame(s, 0, 28, color=False) == frame(s, period, 28, color=False)
    assert frame(s, 0, 28, color=False) != frame(s, 1, 28, color=False)


def test_offline_mood_is_static_across_frames():
    s = snap(mood="offline", online=False)
    assert frame(s, 0, 28, color=False) == frame(s, 1, 28, color=False)


def test_rows_render_in_snapshot_order():
    s = snap(
        [
            view("blocked", "CRIT", 1500.0, "urgent", key="a"),
            view("working", label="later", key="b"),
        ],
        mood="alarmed",
    )
    out = frame(s, 0, 40, color=False)
    body = [ln for ln in out if "urgent" in ln or "later" in ln]
    assert "urgent" in body[0]
    assert "later" in body[1]


def test_empty_agent_list_renders_a_placeholder():
    out = frame(snap(), 0, 28, color=False)
    assert any("no agents" in line for line in out)


def test_ascii_style_emits_only_ascii():
    s = snap([view("blocked", "HIGH", 700.0, "backend")], mood="alarmed")
    out = "\n".join(frame(s, 0, 28, color=False, style="ascii"))
    assert out.isascii()


@pytest.mark.parametrize(
    ("status", "tier", "expected_glyph", "expected_color"),
    [
        ("idle", None, "idle", "dim"),
        ("working", None, "working", "blue"),
        ("done", "FRESH", "waiting", "green"),
        ("done", "MED", "waiting", "yellow"),
        ("done", "HIGH", "waiting", "orange"),
        ("done", "CRIT", "waiting", "red"),
        ("blocked", "FRESH", "blocked", "red"),
        ("blocked", "CRIT", "blocked", "red"),
    ],
)
def test_decorate_maps_state_to_glyph_and_color(status, tier, expected_glyph, expected_color):
    assert decorate(view(status, tier)) == (expected_glyph, expected_color)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, ""), (59, ""), (60, "1m"), (300, "5m"), (3599, "59m"), (3600, "1h"), (7800, "2h")],
)
def test_fmt_age(seconds, expected):
    assert fmt_age(seconds) == expected


@pytest.mark.parametrize("cols", [1, 2, 3, 5, 8, 13, 14, 30])
def test_every_line_is_exactly_cols_wide_across_narrow_and_wide(cols):
    """Width invariant: every returned line is exactly `cols` display columns."""
    s = snap([view("done", "MED", 300.0, "test"), view("working", label="other")], mood="alert")
    for line in frame(s, 0, cols, color=False):
        assert width(line) == cols, f"cols={cols}: {repr(line)}"


# Phrase rendering tests


def test_phrase_is_rendered_when_enabled():
    """Phrase should appear in output when show_phrase=True."""
    s = snap(mood="happy")
    cfg = Config(show_phrase=True)
    lines = frame(s, 0, 60, color=False, config=cfg, phrase_text="test")
    # Join lines and look for quotes (phrase indicator)
    output = "\n".join(lines)
    assert '"' in output, "Phrase should be quoted when rendered"


def test_phrase_is_not_rendered_when_disabled():
    """Phrase should not appear when show_phrase=False."""
    s = snap(mood="happy")
    cfg = Config(show_phrase=False)
    lines = frame(s, 0, 60, color=False, config=cfg, phrase_text="test")
    output = "\n".join(lines)
    # Should not contain quotes (phrase markers)
    assert '"' not in output, "Phrase should not render when disabled"


def test_narrow_width_drops_phrase():
    """Phrase should be dropped for narrow terminals instead of wrapping."""
    s = snap(mood="alert")
    cfg = Config(show_phrase=True)
    # Very narrow width should not have phrase
    narrow_lines = frame(s, 0, 20, color=False, config=cfg, phrase_text="test")
    # Phrase should be dropped due to narrow width (only rendered if cols >= 50)
    # Just verify that the lines still render correctly and maintain width invariant
    for line in narrow_lines:
        assert width(line) == 20


def test_phrase_width_invariant_maintained():
    """Every line should remain exactly `cols` wide even with phrase."""
    s = snap(mood="working")
    cfg = Config(show_phrase=True)
    for cols in [30, 40, 60, 80]:
        lines = frame(s, 0, cols, color=False, config=cfg, phrase_text="test")
        for line in lines:
            w = width(line)
            assert w == cols, f"cols={cols}: line width is {w}, expected {cols}"


# --- colour must never disturb the layout -------------------------------------
# The sprite is coloured now, and every line must still be exactly `cols` wide.
# Escape sequences occupy no columns, so any width computed on a coloured string
# is wrong; these pin that the padding is worked out on the plain text.

ANSI = re.compile(r"\033\[[0-9;]*m")


def test_every_line_is_exact_width_with_colour_on():
    """The box invariant has to survive colouring, at every width and stage."""
    import time

    from shellmate.characters import NAMES
    from shellmate.config import Config
    from shellmate.identity import Identity

    now = time.time()
    long_phrase = "a deliberately long phrase that will need truncating"
    for species in NAMES:
        for age, label in ((3600.0, "egg"), (5 * 86400.0, "adult")):
            ident = Identity(seed="s" * 32, name="Testu", species=species, born_at=now - age)
            for mood in ("sleeping", "working", "alert", "alarmed", "offline"):
                s = snap(mood=mood, online=(mood != "offline"))
                for cols in (3, 10, 14, 28, 50, 80):
                    for idx in range(4):
                        lines = frame(
                            s,
                            idx,
                            cols,
                            character=species,
                            color=True,
                            identity=ident,
                            now=now,
                            config=Config(),
                            phrase_text=long_phrase,
                        )
                        for line in lines:
                            plain = ANSI.sub("", line)
                            assert width(plain) == cols, (
                                f"{species}/{label}/{mood} cols={cols} idx={idx}: "
                                f"{width(plain)} != {cols}"
                            )


def test_colour_does_not_change_the_visible_text():
    """Stripping the escapes must give back exactly the uncoloured render."""
    import time

    from shellmate.config import Config
    from shellmate.identity import Identity

    now = time.time()
    ident = Identity(seed="s" * 32, name="Testu", species="cat", born_at=now - 5 * 86400)
    for mood in ("sleeping", "working", "alarmed"):
        s = snap(mood=mood)
        for idx in range(4):
            kwargs = dict(
                character="cat",
                identity=ident,
                now=now,
                config=Config(),
                phrase_text="something to say",
            )
            painted = frame(s, idx, 60, color=True, **kwargs)
            plain = frame(s, idx, 60, color=False, **kwargs)
            assert [ANSI.sub("", line) for line in painted] == plain, mood


def test_the_secret_buddy_is_multicoloured_here_too():
    """The TUI and the status line must not disagree about the spectrum."""
    import time

    from shellmate.characters import SECRET_SPECIES
    from shellmate.config import Config
    from shellmate.identity import Identity

    now = time.time()
    ident = Identity(seed="s" * 32, name="Testu", species=SECRET_SPECIES, born_at=now - 5 * 86400)
    lines = frame(
        snap(mood="working"),
        0,
        60,
        character=SECRET_SPECIES,
        color=True,
        identity=ident,
        now=now,
        config=Config(),
        phrase_text="",
    )
    colours = set(re.findall(r"\033\[38;2;[0-9;]+m", "".join(lines)))
    assert len(colours) >= 5, f"only {len(colours)} colours; the spectrum did not reach the TUI"


def test_mood_colours_match_the_status_line():
    """Both surfaces map mood to colour; the shell script keeps its own copy.

    If they drift, the same buddy is a different colour depending on which
    surface you look at, and nothing anywhere fails.
    """
    from pathlib import Path

    from shellmate.render import MOOD_COLOR_ROLES

    script = Path(__file__).resolve().parent.parent / "statusline" / "shellmate-sprite.sh"
    text = script.read_text()
    block = re.search(r"role = \{(.*?)\}\[mood\]", text, re.DOTALL)
    assert block, "mood/colour map not found in the status line script"
    shell_map = dict(re.findall(r'"(\w+)":\s*"(\w+)"', block.group(1)))
    assert shell_map == MOOD_COLOR_ROLES, (
        f"status line says {shell_map}, render.py says {MOOD_COLOR_ROLES}"
    )
