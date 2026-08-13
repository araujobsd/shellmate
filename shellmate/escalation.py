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
# How long a per-session phrase slot outlives its session. Long enough that a
# quiet pane keeps its phrase across the gap where its session file has gone
# stale but the pane is still on screen; short enough that closed panes age out.
PHRASE_SLOT_TTL = 3600.0

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
    session_id: str = "",
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
        session_id: pane this call is rendering for. When given, the phrase is
            chosen for that session's mood and kept in that session's own slot.
            When empty, the aggregate mood and the shared slot are used, which is
            what the full-screen app and --face want.
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
    snapshot = Snapshot(views=tuple(views), mood=new_mood, online=online)

    # Track when the mood changed (for stable phrase selection)
    # If mood changed from last time, reset mood_since to now
    if new_mood != state.last_mood:
        mood_since = now

    # The phrase describes what the buddy is showing, and the buddy shows the mood
    # of the pane it is in — so pick the phrase for that mood, not the aggregate.
    display_mood = mood_for_session(snapshot, session_id) if session_id else new_mood

    # Per-session phrase slots, pruned so the dicts cannot grow forever.
    #
    # Liveness alone is the wrong test, and pruning on it was a real bug: session
    # files go stale and are deleted after STALE_SECONDS, so a pane that has been
    # quiet for a while drops out of `live` — which is exactly the pane showing
    # `sleeping`. Any OTHER pane's render then deleted its slot, so on its next
    # render its phrase was empty, it picked a fresh one, and the next pane wiped
    # it again. The sleeping buddy changed what it was saying every two seconds.
    #
    # So a slot survives while its session is live, while it is the pane being
    # rendered, or while it is simply recent. Age is what actually bounds growth:
    # a closed pane stops being written and falls out an hour later.
    cutoff = now - PHRASE_SLOT_TTL

    def _keep(key: str) -> bool:
        if key in live or key == session_id:
            return True
        return state.phrase_set_at_by_session.get(key, 0.0) >= cutoff

    phrase_by_session = {k: v for k, v in state.phrase_by_session.items() if _keep(k)}
    phrase_set_at_by_session = {k: v for k, v in state.phrase_set_at_by_session.items() if _keep(k)}
    last_mood_by_session = {k: v for k, v in state.last_mood_by_session.items() if _keep(k)}

    if session_id:
        phrase_text = phrase_by_session.get(session_id, "")
        phrase_set_at = phrase_set_at_by_session.get(session_id, 0.0)
        old_mood = last_mood_by_session.get(session_id, "sleeping")
    else:
        old_mood = state.last_mood

    # Determine when to pick a NEW phrase (keep existing text otherwise)
    # SIGNAL_MOODS are alert, alarmed, offline (the escalation-indicating moods)
    SIGNAL_MOODS = {"alert", "alarmed", "offline"}
    pick_new_phrase = False

    if phrase_text == "":
        # First run: pick a new phrase
        pick_new_phrase = True
    elif display_mood in SIGNAL_MOODS and old_mood not in SIGNAL_MOODS:
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
            latest_version is not None and display_mood not in SIGNAL_MOODS and int(now) % 4 == 0
        )

        if use_update_phrase:
            phrase_text = update_phrase_for(character, now)
        else:
            phrase_text = phrase_for(character, display_mood, now)

        phrase_set_at = now
    # else: keep existing phrase_text unchanged

    if session_id:
        phrase_by_session[session_id] = phrase_text
        phrase_set_at_by_session[session_id] = phrase_set_at
        last_mood_by_session[session_id] = display_mood
        # Leave the shared slots alone: they belong to the aggregate surfaces, and
        # writing them here is what let panes trample each other.
        phrase_text = state.phrase_text
        phrase_set_at = state.phrase_set_at

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
            phrase_by_session=phrase_by_session,
            phrase_set_at_by_session=phrase_set_at_by_session,
            last_mood_by_session=last_mood_by_session,
        ),
        alerts,
    )
