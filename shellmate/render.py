"""Snapshot -> terminal lines. Pure: no clock, no I/O.

Every returned line is exactly `cols` display columns wide. That invariant is
what keeps the box intact when a tab label contains CJK text or an emoji.
"""

from shellmate.characters import EGG, frames_for, hatch_stage, idle_frame, phrase_for
from shellmate.config import Config
from shellmate.identity import Identity
from shellmate.models import AgentView, Snapshot, fmt_age
from shellmate.textwidth import truncate, width
from shellmate.theme import BOX, COLORS, GLYPHS, RESET, TIER_COLORS

MIN_COLS_FOR_LIST = 14
TITLE = " buddy "
PHRASE_BUDGET = 50  # Max width for phrase area (including quotes and spacing)


def decorate(view: AgentView) -> tuple[str, str]:
    """Map a view to (glyph_role, color_role).

    `blocked` is red at any age — its tier drives notification, never color.
    """
    status = view.agent.status
    if status == "blocked":
        return "blocked", "red"
    if status == "working":
        return "working", "blue"
    if view.tier:
        return "waiting", TIER_COLORS[view.tier]
    return "idle", "dim"


def _pad(text: str, cols: int) -> str:
    """Pad or trim `text` to exactly `cols` display columns."""
    w = width(text)
    if w > cols:
        return truncate(text, cols)
    return text + " " * (cols - w)


def frame(
    snapshot: Snapshot,
    frame_idx: int,
    cols: int,
    *,
    character: str = "",  # empty defers to the registry default via frames_for
    color: bool = True,
    style: str = "unicode",
    identity: Identity | None = None,
    now: float | None = None,
    config: Config | None = None,  # for phrase rendering
    mood_since: float = 0.0,  # timestamp when current mood began
) -> list[str]:
    # Handle cols < 3: can't fit a box, return simple lines exactly `cols` wide
    if cols < 3:
        return [" " * cols] * 3

    box, glyphs = BOX[style], GLYPHS[style]

    def paint(text: str, role: str) -> str:
        return f"{COLORS[role]}{text}{RESET}" if color else text

    def _to_ascii(text: str) -> str:
        """Remove non-ASCII characters from text."""
        return "".join(c for c in text if ord(c) < 128)

    inner = max(cols - 2, 1)

    # Determine which sprite to display: egg, idle variant, or normal mood frame
    sprite = None

    # Check if buddy is hatching
    if identity is not None and now is not None:
        egg_idx = hatch_stage(identity.born_at, now)
        if egg_idx is not None:
            sprite = EGG[egg_idx]

    # Check for idle animation (only if not hatching and during calm moods)
    if sprite is None and identity is not None and snapshot.mood in ("sleeping", "working"):
        idle_variant = idle_frame(character or identity.species, frame_idx)
        if idle_variant is not None:
            sprite = idle_variant

    # Fall back to normal mood frame
    if sprite is None:
        frames = frames_for(character, snapshot.mood)
        sprite = frames[frame_idx % len(frames)]

    # Filter sprite to ASCII if ASCII style is requested
    if style == "ascii":
        sprite = [_to_ascii(row) for row in sprite]

    title = TITLE if inner >= width(TITLE) + 2 else ""
    head = box["h"] + title
    lines = [box["tl"] + head + box["h"] * (inner - width(head)) + box["tr"]]

    # Get phrase if enabled and we have the needed context
    phrase = ""
    if config and config.show_phrase and snapshot.mood and mood_since:
        effective_char = character or identity.species if identity else ""
        phrase = phrase_for(effective_char, snapshot.mood, mood_since)

    # Render sprite lines, adding phrase to the 3rd line if applicable
    for line_no, row in enumerate(sprite):
        padded = _pad(" " + row, inner)

        # On the 3rd line (index 2), try to append the phrase
        if line_no == 2 and phrase and cols >= 50:  # Only if enough room
            # Format phrase as: "phrase" in dim color
            phrase_text = f' "{phrase}"'
            phrase_width = width(phrase_text)

            # Truncate phrase if needed, leaving room for box chars and sprite
            max_phrase_width = inner - width(" " + row)
            if max_phrase_width > 3:  # At least room for a single char + quotes + space
                if phrase_width <= max_phrase_width:
                    padded = _pad(" " + row, inner - phrase_width) + phrase_text
                else:
                    # Truncate the phrase itself
                    truncated = truncate(phrase, max_phrase_width - 3)  # -3 for quotes and space
                    phrase_text = f' "{truncated}"'
                    padded = _pad(" " + row, inner - width(phrase_text)) + phrase_text

        lines.append(box["v"] + padded + box["v"])

    if cols < MIN_COLS_FOR_LIST:
        lines.append(box["bl"] + box["h"] * inner + box["br"])
        return lines

    lines.append(box["ml"] + box["h"] * inner + box["mr"])

    if not snapshot.views:
        body = "no agents" if snapshot.online else "offline"
        lines.append(box["v"] + " " + paint(_pad(body, inner - 1), "dim") + box["v"])
    else:
        for v in snapshot.views:
            glyph_role, color_role = decorate(v)
            glyph = glyphs[glyph_role]
            age = fmt_age(v.age)
            # 1 leading space + glyph + space + label + gap + age
            budget = inner - 2 - width(glyph) - width(age) - 1
            label = truncate(v.agent.label, max(budget, 1))
            gap = inner - 2 - width(glyph) - width(label) - width(age)
            body = f"{glyph} {label}{' ' * max(gap, 1)}{age}"
            lines.append(box["v"] + " " + paint(_pad(body, inner - 1), color_role) + box["v"])

    lines.append(box["bl"] + box["h"] * inner + box["br"])
    return lines
