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


def test_the_scripts_embedded_python_imports_names_that_exist():
    """Every name the shell script imports must exist in the module it names.

    The status line does not import the package the way a test does: it pipes a
    heredoc into python3 with stderr sent to /dev/null, so an ImportError there is
    silent. Removing a symbol from shellmate.theme left this script importing it,
    and the only visible symptom was a blank status line and a warmup_failed
    marker — the whole suite stayed green.

    Checking the names rather than executing the script keeps this a unit test
    while still pinning the seam that the suite cannot otherwise see.
    """
    import ast
    import importlib
    import pathlib
    import re

    script = pathlib.Path(__file__).resolve().parents[1] / "statusline" / "shellmate-sprite.sh"
    text = script.read_text()
    # The heredoc line carries a redirect (<<'PY' 2>/dev/null), so anchor on the
    # marker and skip to end of line rather than expecting a newline right after.
    blocks = re.findall(r"<<'PY'[^\n]*\n(.*?)\nPY\n", text, re.DOTALL)
    assert blocks, "no embedded python found in the status line script"

    checked = 0
    for block in blocks:
        tree = ast.parse(block)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith("shellmate"):
                continue
            module = importlib.import_module(node.module)
            for alias in node.names:
                assert hasattr(module, alias.name), (
                    f"{script.name} imports {alias.name!r} from {node.module}, which no "
                    "longer defines it — the cold render would fail silently"
                )
                checked += 1
    assert checked > 10, f"only {checked} imports checked; the heredoc scan is not finding them"
