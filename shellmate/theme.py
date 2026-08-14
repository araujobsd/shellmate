"""Glyphs and colors.

Every glyph in a set must share one East Asian Width class, box characters
included. Box drawing is EAW=A, so the unicode set is all-A; the ascii set is
all-Na. Mixing classes makes the frame tear unevenly in terminals configured
with ambiguous-width=double, rather than merely rendering wider.
"""

GLYPHS = {
    "unicode": {
        "idle": "○",  # ○ WHITE CIRCLE            EAW=A
        "working": "▶",  # ▶ BLACK RIGHT TRIANGLE    EAW=A
        "waiting": "◎",  # ◎ BULLSEYE                EAW=A
        "blocked": "●",  # ● BLACK CIRCLE            EAW=A
    },
    "ascii": {
        "idle": ".",
        "working": ">",
        "waiting": "*",
        "blocked": "!",
    },
}

BOX = {
    "unicode": {
        "tl": "┌",
        "tr": "┐",
        "bl": "└",
        "br": "┘",
        "h": "─",
        "v": "│",
        "ml": "├",
        "mr": "┤",
    },
    "ascii": {
        "tl": "+",
        "tr": "+",
        "bl": "+",
        "br": "+",
        "h": "-",
        "v": "|",
        "ml": "+",
        "mr": "+",
    },
}

# tokyo-night color palette
COLORS = {
    "dim": "\033[38;2;86;95;137m",
    "blue": "\033[38;2;122;162;247m",
    "green": "\033[38;2;158;206;106m",
    "yellow": "\033[38;2;224;175;104m",
    "orange": "\033[38;2;255;158;100m",
    "red": "\033[38;2;247;118;142m",
}

RESET = "\033[0m"

# Each species keeps one colour in every mood, so the buddy has a stable identity.
# Urgency rides on the mood colour applied to the marks, name and phrase instead.
# Colouring the whole body by mood would make it change appearance whenever you
# stepped away, which is the same flicker that retired size as a signal.
# Every entry is kept at least MIN_MARK_DISTANCE from each colour a mark can be
# painted in — see tests/test_theme.py. The obvious palette failed that: the dog's
# tan was byte-identical to the yellow alert mark and the crab's red to the red
# alarmed mark, so the ! and !! vanished into the body in exactly the moods where
# they matter. Species being similar to EACH OTHER is fine; you only ever see one.
SPECIES_COLORS = {
    "cat": "\033[38;2;222;116;45m",  # ginger
    "owl": "\033[38;2;166;138;100m",  # tawny
    "blob": "\033[38;2;200;140;230m",  # violet
    "dog": "\033[38;2;176;120;70m",  # brown
    "frog": "\033[38;2;90;165;80m",  # green
    "ghost": "\033[38;2;192;202;245m",  # pale
    "penguin": "\033[38;2;90;215;205m",  # ice
    "robot": "\033[38;2;150;150;150m",  # steel
    "cactus": "\033[38;2;70;160;95m",  # sage
    "crab": "\033[38;2;230;90;60m",  # brick
    "octopus": "\033[38;2;200;120;220m",  # magenta
    "dragon": "\033[38;2;255;200;20m",  # gold — the rare one
    "glitch": "\033[38;2;120;230;230m",  # cyan — the secret one
    "ember": "\033[38;2;255;150;40m",  # orange — the other secret one
}

# Colours a mood mark can be painted in, and how far a species must stay from them.
MARK_COLOR_ROLES = ("dim", "blue", "green", "yellow", "red")
MIN_MARK_DISTANCE = 65.0

# Species that render as a spectrum rather than one flat colour. Every entry is
# held to the same MIN_MARK_DISTANCE as a flat species colour, because the mood
# marks are painted immediately beside these glyphs.
SPECTRUM = (
    "\033[38;2;255;85;85m",  # red
    "\033[38;2;255;150;40m",  # orange
    "\033[38;2;255;235;60m",  # yellow
    "\033[38;2;90;240;110m",  # green
    "\033[38;2;100;235;235m",  # cyan
    "\033[38;2;60;120;255m",  # blue
    "\033[38;2;185;130;255m",  # violet
    "\033[38;2;255;110;210m",  # magenta
)

MULTI_COLOR_SPECIES = {"glitch": SPECTRUM}


def multi_color_palette(species: str) -> tuple[str, ...] | None:
    """Spectrum for a species that renders multicoloured, else None. Pure."""
    return MULTI_COLOR_SPECIES.get(species)


def paint_spectrum(line: str, palette: tuple[str, ...], shift: int) -> str:
    """Colour each glyph from the palette, advancing along the line. Pure.

    Spaces are left uncoloured so the escape sequences stay proportional to the
    visible glyphs, and `shift` moves the whole spectrum along per frame, which is
    what makes it crawl rather than merely look striped.
    """
    out = []
    for index, char in enumerate(line):
        if char == " ":
            out.append(char)
            continue
        out.append(palette[(index + shift) % len(palette)] + char)
    return "".join(out) + RESET


# Trailing decorations that belong to the mood rather than the body: ! and !! for
# alert and alarmed, ? for perked, * for happy, z/zz for sleeping, .. for offline.
_MARK_CHARS = "!?*z."


def species_color(species: str) -> str:
    """Colour for a species, falling back to dim for anything unknown. Pure."""
    return SPECIES_COLORS.get(species) or COLORS["dim"]


def split_marks(line: str) -> tuple[str, str]:
    """Split a sprite line into (body, trailing marks). Pure.

    The body is painted in the species colour and the marks in the mood colour,
    so they must be separated first. Only a trailing run counts, and only when
    something separates it from the body: '.' is a mark in '(-.-)..' but must not
    be mistaken for one in the eyes it also appears in.
    """
    end = len(line)
    while end > 0 and line[end - 1] == " ":
        end -= 1
    start = end
    while start > 0 and line[start - 1] in _MARK_CHARS:
        start -= 1
    if start == 0 or start == end or line[start - 1] not in " )]>|/\\^":
        return line, ""
    return line[:start], line[start:]


TIER_COLORS = {"FRESH": "green", "MED": "yellow", "HIGH": "orange", "CRIT": "red"}
