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

TIER_COLORS = {"FRESH": "green", "MED": "yellow", "HIGH": "orange", "CRIT": "red"}
