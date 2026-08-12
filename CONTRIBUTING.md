# Contributing to shellmate

## Adding a buddy

Buddies are the obvious contribution. Adding one is pure data — no logic changes
anywhere. `NAMES` derives from the registry keys, and the CLI iterates `NAMES`, so
a new buddy appears in `--all` and the config picker automatically. If you find
yourself editing `app.py` or `render.py` to make it show up, something is
hardcoded that shouldn't be — please open an issue instead of working around it.

A buddy must appear in **four** registries in `shellmate/characters.py`:

| Registry | What it holds |
|---|---|
| `CHARACTERS` | 7 moods × 2 frames × 3 lines — the main sprite |
| `COMPACT` | 7 one-line faces for the compact surface |
| `BABY` | `sleeping` and `working` only — the hatchling form |
| `PHRASES` | 7 moods × 4–6 short lines in that buddy's voice |

`IDLE` is optional: 2–3 variant frames shown occasionally while `sleeping` or
`working`.

### The contract

Enforced by `tests/test_characters.py`, which is parametrised over the registry —
so it covers your buddy the moment you add it.

- **7 moods:** `sleeping`, `working`, `happy`, `perked`, `alert`, `alarmed`, `offline`
- **2 frames per mood**, and the two frames must **differ** — identical frames mean
  a frozen animation
- **exactly 3 lines per frame**, always. Fixed height keeps the layout from jumping
  when the mood changes
- **≤12 display columns per line**, measured with `textwidth.width()`, never `len()`.
  Several sprites use non-ASCII characters where `len()` lies
- **compact faces ≤8 columns**
- **no two buddies may share a sprite set**, and no two may share a compact face for
  the same mood — they have to stay distinguishable at 7 characters
- **`offline` must look distinct from `sleeping`** — a disconnected buddy must not
  look like a napping one
- **phrases ≤42 columns**, ASCII only, distinct within a mood, and not reused across
  buddies

### Design conventions

These aren't enforced by tests but they're why the existing set works:

**Give it a distinct delimiter.** The compact faces are identified by their
brackets — `=o.o=` cat, `Uo.oU` dog, `{o.o}` owl, `(o.o)` blob, `[o.o]` robot,
`%o.o%` crab. Pick an unused motif and your buddy reads instantly at a glance.

**Signal moods stay plain.** `alert`, `alarmed` and `offline` must look identical at
every age and must not animate idly. They carry information; a blinking alarm is a
worse alarm.

**Give it a voice.** Phrases are half the character. The existing buddies are as
distinguishable by how they talk as by how they look — the cat is aloof, the dog
earnest and shouty, the frog blunt, the robot clipped and machine-like. A new
buddy that sounds like an existing one is a missed opportunity.

**`alarmed` phrases must stay unambiguous.** Funny is fine; anything that undercuts
"something needs you right now" is not.

## No third-party dependencies, ever

shellmate runs on any Python 3.11+ interpreter with nothing installed. That's the
whole install story: clone and run. One runtime dependency forfeits it.

The `no-dependencies` CI job imports the package on a bare interpreter to keep this
honest. `ruff` and `pytest` are development-only and must never be imported by
package code.

## Testing

```bash
ruff check shellmate/ tests/
ruff format --check shellmate/ tests/
python3 -m pytest -q
```

All tests must pass before opening a pull request.

**A note on the shell scripts.** `statusline/shellmate-sprite.sh`,
`hooks/claude-session-state.sh` and `install.sh` are where every real bug in this
project has been — the Python has been fine throughout. If you change them, test
them by *running* them, not just `sh -n`. CI executes the sprite script on Linux
and macOS for exactly this reason. Watch for GNU-only flags: `stat -c` is not
portable, and the script uses a `file_mtime` helper that tries `stat -c` then
`stat -f`.

## Code style

- `ruff` for linting and formatting; `pyproject.toml` is the source of truth.
- Keep logic modules pure. `escalation.py`, `render.py`, `characters.py` and
  `textwidth.py` don't touch the clock, the filesystem, or subprocesses — `now` is
  always a parameter. That's what makes the time-based behaviour testable without
  sleeping.
- Comment intent, not mechanics.
