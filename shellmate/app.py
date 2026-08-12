"""Timer loop and wiring. Deliberately thin — logic lives in the pure modules."""

import argparse
import os
import shutil
import signal
import sys
import time
from pathlib import Path

from shellmate import characters, escalation, render, session, store, theme
from shellmate import config as config_mod
from shellmate import identity as identity_mod
from shellmate.config import Config
from shellmate.models import Snapshot
from shellmate.notify import Notifier
from shellmate.textwidth import width

DEFAULT_COLS = 30


def get_effective_character(cfg: Config, identity_species: str | None) -> str:
    """Determine which character to display based on precedence.

    Precedence: explicit config.character > identity.species > DEFAULT_CHARACTER
    """
    if cfg.character:
        return cfg.character
    if identity_species:
        return identity_species
    return characters.DEFAULT_CHARACTER


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


class App:
    def __init__(self, cfg: Config, state_path: Path, notifier=None):
        self.cfg = cfg
        self.state_path = Path(state_path)
        self.identity_path = store.identity_path()
        self.notifier = notifier if notifier is not None else Notifier()
        self.state = store.load(self.state_path)
        self.identity = store.load_identity(self.identity_path)

        # Initialize identity on first run
        if self.identity is None:
            now = time.time()
            seed = identity_mod.new_seed()
            self.identity = identity_mod.Identity(
                seed=seed,
                name=identity_mod.name_from_seed(seed),
                species=identity_mod.species_from_seed(seed),
                born_at=now,
            )
            store.save_identity(self.identity_path, self.identity)

        # Construct an empty snapshot to avoid clearing loaded state with priming advance call
        self.snapshot = Snapshot(views=(), mood="sleeping", online=True)
        self._last_poll: float | None = None
        self._frame = 0
        self._running = True

    def tick(self, now: float, cols: int) -> list[str]:
        if self._last_poll is None or now - self._last_poll >= self.cfg.poll_seconds:
            agents, online = session.sample()
            self.snapshot, self.state, alerts = escalation.advance(
                agents, self.state, now, self.cfg, online
            )
            self._last_poll = now
            if self.cfg.notify and self.notifier is not None:
                for alert in alerts:
                    if not self.notifier.enabled:
                        break
                    self.notifier.send(alert)

        identity_species = self.identity.species if self.identity else None
        effective_character = get_effective_character(self.cfg, identity_species)

        lines = render.frame(
            self.snapshot,
            self._frame,
            cols,
            character=effective_character,
            color=color_enabled(),
            style="ascii" if self.cfg.ascii_glyphs else "unicode",
            identity=self.identity,
            now=now,
            config=self.cfg,
            mood_since=self.state.mood_since,
        )
        self._frame += 1
        return lines

    def shutdown(self) -> None:
        store.save(self.state_path, self.state)

    def stop(self, *_args) -> None:
        self._running = False

    def run(self) -> int:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        sys.stdout.write("\033[?25l")  # hide cursor
        try:
            while self._running:
                cols = shutil.get_terminal_size((DEFAULT_COLS, 24)).columns
                lines = self.tick(time.time(), cols)
                sys.stdout.write("\033[H\033[J" + "\n".join(lines) + "\n")
                sys.stdout.flush()
                time.sleep(self.cfg.frame_seconds)
        finally:
            sys.stdout.write("\033[?25h")  # restore cursor
            sys.stdout.flush()
            self.shutdown()
        return 0


def show_face() -> int:
    """Poll once, advance state, render compact face to stdout, exit 0.

    Never sends notifications regardless of escalation tier. The statusline runs
    ~10 concurrent invocations per render; each must be silent to avoid notification spam.
    """
    try:
        cfg = config_mod.load_config()
        agents, online = session.sample()
        state = store.load(store.default_path())
        identity = store.load_identity(store.identity_path())
        snapshot, new_state, _alerts = escalation.advance(agents, state, time.time(), cfg, online)
        store.save(store.default_path(), new_state)

        identity_species = identity.species if identity else None
        effective_character = get_effective_character(cfg, identity_species)

        face = characters.compact_for(effective_character, snapshot.mood)
        colors_enabled = color_enabled()
        mood_color_map = {
            "sleeping": theme.COLORS["dim"],
            "working": theme.COLORS["blue"],
            "perked": theme.COLORS["green"],
            "alert": theme.COLORS["yellow"],
            "alarmed": theme.COLORS["red"],
            "offline": theme.COLORS["dim"],
        }
        color = mood_color_map.get(snapshot.mood, theme.COLORS["dim"])
        reset = theme.RESET if colors_enabled else ""
        color_code = color if colors_enabled else ""

        sys.stdout.write(f"{color_code}{face}{reset}\n")
        sys.stdout.flush()
        return 0
    except Exception:
        # On any error, print offline face so statusline doesn't vanish
        face = characters.compact_for("", "offline")
        sys.stdout.write(f"{face}\n")
        sys.stdout.flush()
        return 0


def show_sprite() -> int:
    """Poll once, advance state, render full sprite, and exit 0.

    Never sends notifications regardless of escalation tier. The statusline runs
    ~10 concurrent invocations per render; each must be silent to avoid notification spam.
    """
    try:
        cfg = config_mod.load_config()
        agents, online = session.sample()
        state = store.load(store.default_path())
        identity = store.load_identity(store.identity_path())
        now = time.time()

        # Initialize identity if needed
        if identity is None:
            seed = identity_mod.new_seed()
            identity = identity_mod.Identity(
                seed=seed,
                name=identity_mod.name_from_seed(seed),
                species=identity_mod.species_from_seed(seed),
                born_at=now,
            )
            store.save_identity(store.identity_path(), identity)

        snapshot, new_state, _alerts = escalation.advance(agents, state, now, cfg, online)
        store.save(store.default_path(), new_state)

        # Determine which character to use: config > identity.species > default
        identity_species = identity.species if identity else None
        effective_character = get_effective_character(cfg, identity_species)

        # Get the sprite directly without box wrapper
        from shellmate.characters import EGG, frames_for, hatch_stage, idle_frame

        sprite = None
        # Check if buddy is hatching
        if identity:
            egg_idx = hatch_stage(identity.born_at, now)
            if egg_idx is not None:
                sprite = EGG[egg_idx]

        # Check for idle animation
        if sprite is None and identity and snapshot.mood in ("sleeping", "working"):
            idle_variant = idle_frame(effective_character, 0)
            if idle_variant is not None:
                sprite = idle_variant

        # Fall back to normal mood frame
        if sprite is None:
            frames = frames_for(effective_character, snapshot.mood)
            sprite = frames[0]

        # Render sprite with color
        colors_enabled = color_enabled()
        mood_color_map = {
            "sleeping": theme.COLORS["dim"],
            "working": theme.COLORS["blue"],
            "perked": theme.COLORS["green"],
            "alert": theme.COLORS["yellow"],
            "alarmed": theme.COLORS["red"],
            "offline": theme.COLORS["dim"],
        }
        color = mood_color_map.get(snapshot.mood, theme.COLORS["dim"])
        reset = theme.RESET if colors_enabled else ""
        color_code = color if colors_enabled else ""

        for line in sprite:
            sys.stdout.write(f"{color_code}{line}{reset}\n")
        sys.stdout.flush()
        return 0
    except Exception:
        # On any error, print blank lines
        for _ in range(3):
            sys.stdout.write("\n")
        sys.stdout.flush()
        return 0


def pet() -> int:
    """Record a petting event and print species-specific affectionate line.

    Updates pet_count and petted_at in state.json. Never uses Notifier.
    Exit 0 with one line of text.
    """
    try:
        state = store.load(store.default_path())
        identity = store.load_identity(store.identity_path())
        now = time.time()

        # Initialize identity if needed
        if identity is None:
            seed = identity_mod.new_seed()
            identity = identity_mod.Identity(
                seed=seed,
                name=identity_mod.name_from_seed(seed),
                species=identity_mod.species_from_seed(seed),
                born_at=now,
            )
            store.save_identity(store.identity_path(), identity)

        # Increment pet count and update petted_at timestamp
        state.pet_count += 1
        state.petted_at = now
        store.save(store.default_path(), state)

        # Print species-specific affectionate line
        affectionate_lines = {
            "cat": "purrs softly",
            "dog": "wags tail happily",
            "owl": "hoots softly",
            "blob": "wobbles gently",
        }
        line = affectionate_lines.get(identity.species, "seems pleased")
        sys.stdout.write(f"{line}\n")
        sys.stdout.flush()
        return 0
    except Exception:
        sys.stdout.flush()
        return 0


def show_phrase() -> int:
    """Poll once, get current phrase, and exit 0.

    Prints just the phrase for the current mood, no color, no quotes.
    """
    try:
        cfg = config_mod.load_config()
        agents, online = session.sample()
        state = store.load(store.default_path())
        identity = store.load_identity(store.identity_path())
        now = time.time()

        # Initialize identity if needed
        if identity is None:
            seed = identity_mod.new_seed()
            identity = identity_mod.Identity(
                seed=seed,
                name=identity_mod.name_from_seed(seed),
                species=identity_mod.species_from_seed(seed),
                born_at=now,
            )
            store.save_identity(store.identity_path(), identity)

        snapshot, new_state, _alerts = escalation.advance(agents, state, now, cfg, online)
        store.save(store.default_path(), new_state)

        identity_species = identity.species if identity else None
        effective_character = get_effective_character(cfg, identity_species)

        phrase = characters.phrase_for(effective_character, snapshot.mood, new_state.mood_since)
        sys.stdout.write(f"{phrase}\n")
        sys.stdout.flush()
        return 0
    except Exception:
        sys.stdout.flush()
        return 0


def show_whoami() -> int:
    """Print buddy's name, species, age, stage, and pet count, then exit 0."""
    try:
        agents, online = session.sample()
        identity = store.load_identity(store.identity_path())
        state = store.load(store.default_path())
        now = time.time()

        # Initialize identity if needed
        if identity is None:
            seed = identity_mod.new_seed()
            identity = identity_mod.Identity(
                seed=seed,
                name=identity_mod.name_from_seed(seed),
                species=identity_mod.species_from_seed(seed),
                born_at=now,
            )
            store.save_identity(store.identity_path(), identity)

        if identity:
            age = identity_mod.age_label(identity.born_at, now)
            stage = characters.stage_for(identity.born_at, now)

            # Map stage to label (only show non-adult stages)
            stage_labels = {
                "egg": "(egg)",
                "hatchling": "(hatchling)",
                "juvenile": "(juvenile)",
            }
            stage_label = stage_labels.get(stage, "")

            # The rolled species and the displayed one can differ, because
            # config.character overrides the roll. Reporting only the roll is
            # misleading (the user sees a penguin but is told "the blob");
            # reporting only the override hides what they rolled. Show both,
            # but only when they actually differ.
            cfg = config_mod.load_config()
            shown = cfg.character or identity.species
            output = f"{identity.name} the {identity.species}"
            if shown != identity.species:
                output += f", shown as {shown}"
            output += f", {age}"
            if stage_label:
                output += f" {stage_label}"
            if state.pet_count > 0:
                times_label = "time" if state.pet_count == 1 else "times"
                output += f", petted {state.pet_count} {times_label}"

            sys.stdout.write(output + "\n")
        sys.stdout.flush()
        return 0
    except Exception:
        sys.stdout.flush()
        return 0


def show_all_characters() -> int:
    """Display all available characters and moods without starting the loop."""
    mood_descriptions = {
        "sleeping": "all agents idle",
        "working": "something is running",
        "perked": "just finished (<2m)",
        "alert": "waiting 2-10m",
        "alarmed": "blocked, or ignored >10m",
        "offline": "connection lost",
    }

    config_path = "~/.config/shellmate/config.toml"
    sys.stdout.write(f"Configuration: add to {config_path}\n\n")

    for char_name in characters.NAMES:
        # Mark the default character and make the name visually distinct
        marker = "  (default)" if char_name == characters.DEFAULT_CHARACTER else ""
        sys.stdout.write(f"{'=' * 40}\n")
        sys.stdout.write(f"{char_name.upper()}{marker}\n")
        sys.stdout.write(f'  character = "{char_name}"\n')
        sys.stdout.write("\n")

        for mood in characters.MOODS:
            frames = characters.frames_for(char_name, mood)
            description = mood_descriptions.get(mood, "")

            # Print mood name and description
            sys.stdout.write(f"  {mood:<10} {description}\n")

            # Get frames (offline has 1, others have 2)
            frame_0 = frames[0] if frames else None
            frame_1 = frames[1] if len(frames) > 1 else None

            if frame_0:
                # Print two frames side by side with proper padding
                for line_idx in range(characters.SPRITE_LINES):
                    line_0 = frame_0[line_idx] if line_idx < len(frame_0) else ""
                    line_1 = frame_1[line_idx] if frame_1 and line_idx < len(frame_1) else ""

                    # Calculate padding needed based on display width
                    line_0_width = width(line_0)
                    padding = " " * (characters.SPRITE_MAX_COLS - line_0_width + 2)

                    sys.stdout.write(f"    {line_0}{padding}{line_1}\n")

            sys.stdout.write("\n")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shellmate")
    parser.add_argument(
        "--all",
        action="store_true",
        help="show all available buddies and exit",
    )
    parser.add_argument(
        "--face",
        action="store_true",
        help="poll once, print compact face, and exit (for statusline integration)",
    )
    parser.add_argument(
        "--sprite",
        action="store_true",
        help="poll once, print full 3-line sprite, and exit (for statusline integration)",
    )
    parser.add_argument(
        "--whoami",
        action="store_true",
        help="print buddy's name, species, and age, then exit",
    )
    parser.add_argument(
        "--pet",
        action="store_true",
        help="pet your buddy and print affectionate response, then exit",
    )
    parser.add_argument(
        "--say",
        action="store_true",
        help="print buddy's current mood phrase, then exit",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.all:
        return show_all_characters()

    if args.face:
        return show_face()

    if args.sprite:
        return show_sprite()

    if args.whoami:
        return show_whoami()

    if args.pet:
        return pet()

    if args.say:
        return show_phrase()

    cfg = config_mod.load_config()
    app = App(cfg=cfg, state_path=store.default_path())
    return app.run()
