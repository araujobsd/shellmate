# Historical design documents

**These documents describe a product that no longer exists.** They are kept for
context on how shellmate got here, not as documentation of what it does. For
that, read the top-level `README.md`.

## What changed

shellmate began as `herdr-buddy`, a plugin for the [herdr](https://herdr.dev)
terminal multiplexer. It was designed as a **sentinel**: a status indicator with
a face, living in a dedicated pane, whose expression aggregated the state of every
coding agent running under herdr, escalating to a desktop notification when one
had been finished-or-blocked and ignored.

Three things then changed, in order:

1. **The surface was wrong.** A dedicated pane is somewhere you navigate to. What
   was actually wanted was company — something present while you work, not a
   destination. The pane was replaced by an animated sprite rendered above the
   Claude Code status line.

2. **The premise was wrong.** The escalation clock started when an agent's status
   became `done` or `blocked`. Probing live herdr for 91 minutes across 10 agents
   recorded **zero** occurrences of either state — only `idle` and `working`. The
   rule was rewritten to trigger on the `working` → not-`working` *transition*,
   which is correct regardless of which resting state the harness reports.

3. **herdr was dropped entirely.** The audience became Claude Code users
   generally, most of whom do not run herdr. Session state now comes from Claude
   Code hooks, and the project was renamed from `herdr-buddy` to `shellmate`.

## What survived

The engine. Escalation, mood derivation, the sprite registry, display-width
arithmetic, atomic state persistence, and the notifier were all written against
the original design and carried through every pivot without rework. Only the data
source and the rendering surface were replaced.

## Reading these documents

- `2026-08-12-original-herdr-design.md` — the approved design spec
- `2026-08-12-original-herdr-plan.md` — the implementation plan built from it

Both describe herdr integration, a pane-based UI, and a status-based escalation
rule. **None of those are how shellmate works now.** Where they conflict with the
code, the code is right.
