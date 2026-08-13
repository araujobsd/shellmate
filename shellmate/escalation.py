"""Pure escalation state machine.

`now` is always a parameter — this module never reads the clock. That is what
makes every tier transition testable without sleeping.
"""

from shellmate.characters import phrase_for, update_phrase_for
from shellmate.config import Config
from shellmate.models import Agent, AgentView, Alert, EscalationState, Snapshot

NOTIFY_TIERS = ("HIGH", "CRIT")
COOLDOWN_SECONDS = 60.0
PHRASE_MIN_SECONDS = 90.0

_TIER_RANK = {"CRIT": 0, "HIGH": 1, "MED": 2, "FRESH": 3}


def tier_for(age: float, cfg: Config) -> str:
    if age >= cfg.crit_seconds:
        return "CRIT"
    if age >= cfg.high_seconds:
        return "HIGH"
    if age >= cfg.med_seconds:
        return "MED"
    return "FRESH"


def mood_for(views: tuple[AgentView, ...], online: bool) -> str:
    """First match wins. Offline outranks everything."""
    if not online:
        return "offline"
    tiers = {v.tier for v in views if v.tier}
    if any(v.agent.status == "blocked" for v in views):
        return "alarmed"
    if tiers & {"HIGH", "CRIT"}:
        return "alarmed"
    if "MED" in tiers:
        return "alert"
    if "FRESH" in tiers:
        return "perked"
    if any(v.agent.status == "working" for v in views):
        return "working"
    return "sleeping"


def mood_for_session(snapshot: Snapshot, session_id: str) -> str:
    """Get the mood for ONE session rather than the aggregate.

    Returns the mood reflecting that specific session's state:
      - offline if snapshot.online is False
      - "alarmed" if the session's view is blocked or tier HIGH/CRIT
      - "alert" if the session's view is tier MED
      - "perked" if the session's view is tier FRESH
      - "working" if the session's view has status working
      - "sleeping" if the session is not present or idle
    """
    if not snapshot.online:
        return "offline"

    # Find the AgentView for this session_id
    session_view = None
    for view in snapshot.views:
        if view.agent.key == session_id:
            session_view = view
            break

    # Unknown session or never heard from it: sleeping
    if session_view is None:
        return "sleeping"

    # Apply the same mood ladder as aggregate but for one session
    if session_view.agent.status == "blocked":
        return "alarmed"
    if session_view.tier in ("HIGH", "CRIT"):
        return "alarmed"
    if session_view.tier == "MED":
        return "alert"
    if session_view.tier == "FRESH":
        return "perked"
    if session_view.agent.status == "working":
        return "working"
    return "sleeping"


def _sort_key(view: AgentView) -> tuple[int, float]:
    if view.tier:
        return (_TIER_RANK[view.tier], -view.age)
    return (4 if view.agent.status == "working" else 5, 0.0)


def _is_waiting(
    agent: Agent,
    prev_status: str | None,
    has_timer: bool,
) -> bool:
    """Determine if an agent is waiting based on transition-based rules.

    Rules (evaluated in order):
    1. working -> NOT waiting, clear timer
    2. blocked -> waiting immediately
    3. done -> waiting immediately (explicit completion signal from Stop hook)
    4. previous status was working and current is not -> waiting (clock starts)
    5. has a running timer and still not working -> waiting
    6. idle never seen working -> NOT waiting
    7. otherwise -> NOT waiting
    """
    if agent.status == "working":
        return False
    if agent.status == "blocked":
        return True
    if agent.status == "done":
        return True
    if prev_status == "working" and agent.status != "working":
        return True
    return has_timer and agent.status != "working"


def advance(
    agents: list[Agent],
    state: EscalationState,
    now: float,
    cfg: Config,
    online: bool,
    character: str = "",
    latest_version: str | None = None,
) -> tuple[Snapshot, EscalationState, list[Alert]]:
    """Fold a poll result into the escalation state.

    Returns a new state; the input is never mutated.

    Args:
        agents: list of agents to poll
        state: current escalation state
        now: current timestamp
        cfg: configuration
        online: whether the session is online
        character: buddy character name
        latest_version: newer version available (if any), for update notifications
    """
    live = {a.key for a in agents}
    waiting_since = {k: v for k, v in state.waiting_since.items() if k in live}
    notified = {k: list(v) for k, v in state.notified.items() if k in live}
    last_status = {k: v for k, v in state.last_status.items() if k in live}
    last_alert_at = state.last_alert_at
    mood_since = state.mood_since  # Track when current mood began
    phrase_text = state.phrase_text  # the rendered phrase to display
    phrase_set_at = state.phrase_set_at  # when phrase_text was chosen
    latest_version = latest_version or state.latest_version  # Persist if not updated

    views = []
    alerts: list[Alert] = []

    for a in agents:
        prev_status = last_status.get(a.key)
        has_timer = a.key in waiting_since
        is_waiting = _is_waiting(a, prev_status, has_timer)

        if not is_waiting:
            waiting_since.pop(a.key, None)
            notified.pop(a.key, None)
            views.append(AgentView(agent=a, age=0.0, tier=None))
        else:
            started = waiting_since.setdefault(a.key, now)
            age = max(now - started, 0.0)
            tier = tier_for(age, cfg)
            views.append(AgentView(agent=a, age=age, tier=tier))

            if online and tier in NOTIFY_TIERS:
                already = notified.setdefault(a.key, [])
                if tier not in already and now - last_alert_at >= COOLDOWN_SECONDS:
                    already.append(tier)
                    last_alert_at = now
                    alerts.append(Alert(key=a.key, label=a.label, tier=tier, age=age))

        last_status[a.key] = a.status

    views.sort(key=_sort_key)
    new_mood = mood_for(tuple(views), online)

    # Track when the mood changed (for stable phrase selection)
    # If mood changed from last time, reset mood_since to now
    if new_mood != state.last_mood:
        mood_since = now

    # Determine when to pick a NEW phrase (keep existing text otherwise)
    # SIGNAL_MOODS are alert, alarmed, offline (the escalation-indicating moods)
    SIGNAL_MOODS = {"alert", "alarmed", "offline"}
    old_mood = state.last_mood
    pick_new_phrase = False

    if phrase_text == "":
        # First run: pick a new phrase
        pick_new_phrase = True
    elif new_mood in SIGNAL_MOODS and old_mood not in SIGNAL_MOODS:
        # Escalation: entering SIGNAL from non-SIGNAL, pick new phrase immediately
        pick_new_phrase = True
    elif now - phrase_set_at >= PHRASE_MIN_SECONDS:
        # Minimum lifetime elapsed: allow picking new phrase
        pick_new_phrase = True

    if pick_new_phrase:
        # Decide whether to show an update phrase (roughly 1 in 4 times, deterministically)
        # Use the phrase seed to decide: if seed % 4 == 0, show update phrase
        # Only show update phrases for non-distress moods (never override alert/alarmed/offline)
        use_update_phrase = (
            latest_version is not None and new_mood not in SIGNAL_MOODS and int(now) % 4 == 0
        )

        if use_update_phrase:
            phrase_text = update_phrase_for(character, now)
        else:
            phrase_text = phrase_for(character, new_mood, now)

        phrase_set_at = now
    # else: keep existing phrase_text unchanged

    snapshot = Snapshot(views=tuple(views), mood=new_mood, online=online)
    return (
        snapshot,
        EscalationState(
            waiting_since=waiting_since,
            notified=notified,
            last_alert_at=last_alert_at,
            last_status=last_status,
            petted_at=state.petted_at,
            pet_count=state.pet_count,
            last_mood=new_mood,
            mood_since=mood_since,
            phrase_text=phrase_text,
            phrase_set_at=phrase_set_at,
            latest_version=latest_version,
        ),
        alerts,
    )
