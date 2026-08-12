"""Display-column arithmetic.

Never use len() on text bound for the terminal. A CJK or emoji label passes a
len() check and then renders at double width, tearing the layout.
"""

import unicodedata

_WIDE = frozenset({"W", "F"})


def _char_width(ch: str) -> int:
    """Return the terminal columns a single character occupies."""
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in _WIDE else 1


def width(text: str) -> int:
    """Return the number of terminal columns `text` occupies."""
    return sum(_char_width(ch) for ch in text)


def truncate(text: str, budget: int, ellipsis: str = "…") -> str:
    """Shorten `text` so it fits `budget` columns, appending `ellipsis` if cut.

    Guarantees width(result) <= budget for any input, including a budget too
    small to hold the ellipsis itself.
    """
    if budget <= 0:
        return ""
    if width(text) <= budget:
        return text

    marker_w = width(ellipsis)
    if budget < marker_w:
        return ""

    allowance = budget - marker_w
    used = 0
    cut = []
    for ch in text:
        w = _char_width(ch)
        if used + w > allowance:
            break
        cut.append(ch)
        used += w
    return "".join(cut) + ellipsis
