"""User configuration. A bad config file must never prevent startup."""

import os
import sys
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

# NOTE: config deliberately does NOT validate `character` against the sprite
# registry. Importing characters here would make config depend on a later task,
# and `characters.frames_for()` already falls back for an unknown name. Keeping
# the fallback in exactly one place means renaming a buddy is a single edit.


@dataclass(frozen=True)
class Config:
    # Empty means "whatever the sprite registry defaults to". Naming a specific
    # buddy here would be a second place to edit when the buddies get renamed.
    character: str = ""
    poll_seconds: float = 2.0
    frame_seconds: float = 0.6
    notify: bool = False  # Claude sessions are interactive; notifications disabled by default
    med_seconds: int = 120
    high_seconds: int = 600
    crit_seconds: int = 1200
    ascii_glyphs: bool = False
    show_name: bool = True  # Show buddy's name in statusline sprite
    show_phrase: bool = True  # Show mood-specific phrases in statusline


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "shellmate" / "config.toml"


def load_config(path: Path | None = None) -> Config:
    """Read config, falling back to defaults for anything missing or invalid."""
    path = path or default_path()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return Config()

    # dataclasses.fields() yields f.type as the actual class object here (not a
    # string) because this module does not use `from __future__ import
    # annotations`. Compare with `is`, never against a string literal — a string
    # comparison silently matches nothing and every config value is discarded.
    types = {f.name: f.type for f in fields(Config)}
    values = {}
    for name, declared in types.items():
        if name not in raw:
            continue
        val = raw[name]
        # bool is a subclass of int, so it must be tested before the numeric branches
        if declared is bool:
            ok = isinstance(val, bool)
        elif declared is float:
            ok = isinstance(val, (int, float)) and not isinstance(val, bool)
            val = float(val) if ok else val
        elif declared is int:
            ok = isinstance(val, int) and not isinstance(val, bool)
        else:
            ok = isinstance(val, str)
        if ok:
            values[name] = val

    cfg = Config(**values)
    if cfg.poll_seconds <= 0 or cfg.frame_seconds <= 0:
        print("shellmate: non-positive interval in config, using defaults", file=sys.stderr)
        return Config()
    return cfg
