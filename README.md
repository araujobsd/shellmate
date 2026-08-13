# shellmate

A terminal pet that lives above your Claude Code status line. It hatches from an
egg, gets a name, ages, reacts to your coding sessions, and says things.

```
  .---.
 ( o.o )  Kizuhi
  `---'   "blobbing in solidarity"
you@laptop  my-project (main*)  Opus 5  ctx:47%  sess:$0.41
```

## Install

**The easy way — ask Claude to do it.** Paste this into any Claude Code session:

```
Install shellmate from https://github.com/araujobsd/shellmate — clone it to
~/dev/shellmate and run ./install.sh, then show me what it changed.
```

**Or do it yourself:**

```bash
git clone https://github.com/araujobsd/shellmate.git ~/dev/shellmate
cd ~/dev/shellmate && ./install.sh
```

Either way, reload Claude Code afterwards. Your buddy starts as an egg.

The installer backs up `~/.claude/settings.json` first, adds four hooks, sets
`statusLine.refreshInterval`, and installs the `/petbuddy` command. **If you
already have a status line command it will not overwrite it** — it prints the two
lines to add to your own script instead.

Requirements: Claude Code, `python3` 3.11+. No other dependencies, ever.

## Your buddy

It hatches once, then it's yours:

| Stage | Age | What you see |
|---|---|---|
| egg | first 8 hours | an egg that cracks progressively, and mutters |
| hatchling | 8h – 2 days | a small version of your buddy |
| juvenile | 2 – 4 days | full size |
| adult | 4 days on | full size |

```bash
python3 -m shellmate --whoami     # Kizuhi the blob, 3d old (juvenile), petted 6 times
python3 -m shellmate --all        # every buddy, every mood, side by side
```

Species and name are rolled once from a random seed at first hatch and persist in
`~/.local/state/shellmate/identity.json`. Delete that file to roll a new buddy.
The seed is a random UUID — it is not derived from your username, hostname or
account, so your buddy's identity says nothing about you.

Override the roll any time:

```toml
# ~/.config/shellmate/config.toml
character = "octopus"
```

## Moods

The face reflects the session in *that pane*, not an aggregate — your buddy in a
quiet conversation stays quiet even while another session is busy.

| Mood | Means |
|---|---|
| sleeping | nothing happening in this session |
| working | Claude is working here |
| perked | a turn just finished |
| alert | finished and waiting ~2 minutes |
| alarmed | waiting past 10 minutes, or blocked |
| happy | you just petted it |
| offline | shellmate can't see session state |

`alert`, `alarmed` and `offline` look identical at every age and never animate
idly — they carry a signal, so they stay legible.

## Petting

```
/petbuddy
```

Or `python3 -m shellmate --pet`. Your buddy is visibly happy for 10 seconds and
the count goes in `--whoami`. Petting never overrides `alert`, `alarmed` or
`offline` — a pet cannot hide the fact that something needs you.

## Characters

Eleven. Each has its own face, compact form, hatchling variant, idle behaviour,
and about 30 phrases in its own voice — 338 in total across the roster.

| | | |
|---|---|---|
| **cat** `=o.o=` aloof, faintly judgmental | **owl** `{o.o}` dry, formal | **blob** `(o.o)` literal, absurd |
| **dog** `Uo.oU` earnest, shouty | **frog** `@o.o@` blunt, monosyllabic | **ghost** `~o.o~` wistful, trails off |
| **penguin** `<o.o>` pompous, dignified | **robot** `[o.o]` terse, machine-like | **cactus** `\|o.o\|` stoic, needs nothing |
| **crab** `%o.o%` sideways thinker | **octopus** `8o.o8` frazzled, many-handed | |

```
   \|/          (\ /)         ,-^-.
  |(o.o)|      ( o.o )       (~o.o~)
   |___|        /'-'\         ~|~|~
  cactus         crab         octopus
```

## Configuration

`~/.config/shellmate/config.toml` — every field optional.

| Field | Default | Notes |
|---|---|---|
| `character` | `""` | Empty uses your rolled species. Any name from the roster overrides it. |
| `show_name` | `true` | Show the buddy's name beside the sprite. |
| `show_phrase` | `true` | Show what it's saying. A phrase holds for at least 90 seconds so it doesn't flicker as the mood moves; escalation overrides that immediately. |
| `notify` | `false` | Desktop notification when a session is ignored past `high_seconds`. Off by default — see below. |
| `poll_seconds` | `2.0` | How often session state is sampled. |
| `frame_seconds` | `0.6` | Animation frame interval. |
| `med_seconds` | `120` | Waiting this long → `alert`. |
| `high_seconds` | `600` | Waiting this long → `alarmed`, and notifies if enabled. |
| `crit_seconds` | `1200` | Waiting this long → notifies a second time if enabled. |
| `ascii_glyphs` | `false` | Pure-ASCII glyphs and box characters, for terminals that render ambiguous-width characters inconsistently. |

**Notifications are off by default and that is deliberate.** For a solo
interactive session, sitting `done` for ten minutes is normal — you're reading
output or getting coffee. Toasting you for that is obnoxious. Turn them on if you
run several sessions in parallel and want to be told when one has been ignored.

## How it works

Claude Code hooks (`UserPromptSubmit`, `Stop`, `SessionStart`, `SessionEnd`) write
one small JSON file per session to `~/.local/state/shellmate/sessions/`. The
status line script reads those, works out the mood for the current session, and
renders a sprite.

Two details that matter if you're reading the code:

**The hot path is pure shell.** Your status line re-renders about once a second in
every pane. Rendering with Python each time cost ~110 ms and over a CPU-second per
second across ten panes. So a backgrounded cold path pre-renders both animation
frames to disk every couple of seconds, and the per-render path just `cat`s one —
about 10 ms. The frame index comes from the wall clock, so all panes animate in
sync.

**Stale caches show as offline.** If the cold path breaks, the cached frames stay
on disk and would keep alternating from the clock — the buddy would look alive
while showing dead state. Frames older than ~12 seconds render the `offline` face
instead. A dead buddy should look dead.

## Uninstall

```bash
./install.sh --uninstall
```

Removes what it added and restores your settings. Your buddy's identity survives
in `~/.local/state/shellmate/identity.json` — delete that too if you want it gone.

## Prior art

[coding-buddy](https://github.com/ramarivera/coding-buddy) does something similar
and does it well: 19 species, rarity tiers, stats, and speech written by the model
itself through an MCP tool. If you want the richer thing, install that. It needs
Bun and `jq`.

shellmate is smaller and needs neither — just the `python3` you already have.
