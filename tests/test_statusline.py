"""Guards for the status line shell script.

Every bug that ever reached a user in this project lived in the shell layer, and
the Python suite cannot see it. These tests read the script as text and check the
few facts that must stay true.
"""

import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "statusline" / "shellmate-sprite.sh"


def test_script_exists():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_shell_frame_count_matches_max_frames():
    """The hot path indexes cache slots in pure bash, so the count is duplicated.

    If FRAMES drops below MAX_FRAMES the extra frames are written and never shown;
    if it rises above, the hot path cats a file the cold path never wrote and the
    buddy blinks out. Neither raises anywhere, so pin them together.
    """
    from shellmate.characters import MAX_FRAMES

    match = re.search(r"^FRAMES=(\d+)$", SCRIPT.read_text(), re.MULTILINE)
    assert match, "FRAMES= not found in the status line script"
    assert int(match.group(1)) == MAX_FRAMES, (
        f"shell FRAMES={match.group(1)} but characters.MAX_FRAMES={MAX_FRAMES}"
    )


def test_cold_path_passes_the_character_to_advance():
    """Without character=, phrase selection silently falls back to the default
    species and every non-cat buddy speaks in the cat's voice."""
    text = SCRIPT.read_text()
    call = re.search(r"snap, st, _ = advance\((.*?)\)  #", text, re.DOTALL)
    assert call, "advance() call not found"
    assert "character=effective_character" in call.group(1)
    assert "session_id=session_id" in call.group(1)
