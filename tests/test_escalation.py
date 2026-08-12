import pytest

from shellmate.config import Config
from shellmate.escalation import advance, mood_for, mood_for_session, tier_for
from shellmate.models import Agent, AgentView, EscalationState, Snapshot

CFG = Config()


def agent(key="a", status="idle", label="tab"):
    return Agent(key=key, status=status, label=label, pane_id="p", tab_id="t")


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, "FRESH"),
        (119, "FRESH"),
        (120, "MED"),
        (599, "MED"),
        (600, "HIGH"),
        (1199, "HIGH"),
        (1200, "CRIT"),
        (99999, "CRIT"),
    ],
)
def test_tier_boundaries(age, expected):
    assert tier_for(age, CFG) == expected


def test_working_to_idle_starts_clock():
    """Transition from working to idle starts the waiting clock."""
    state = EscalationState()
    # First poll: agent is working
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    # Second poll: agent transitions to idle
    snap, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    assert state.waiting_since["a"] == 0.0
    assert snap.views[0].age == 0.0


def test_working_to_done_starts_clock():
    """Transition from working to done starts the waiting clock."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    snap, state, _ = advance([agent(status="done")], state, now=0.0, cfg=CFG, online=True)
    assert state.waiting_since["a"] == 0.0
    assert snap.views[0].age == 0.0


def test_idle_since_startup_does_not_escalate():
    """An agent idle since startup never enters waiting."""
    state = EscalationState()
    # Walk an always-idle agent past all thresholds
    snap, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    assert snap.views[0].tier is None
    snap, state, _ = advance([agent(status="idle")], state, now=1300.0, cfg=CFG, online=True)
    assert snap.views[0].tier is None
    assert state.waiting_since == {}
    assert len([a for a in [] if a.tier]) == 0  # No alerts


def test_blocked_on_first_sight_starts_clock():
    """An agent with blocked status starts the clock immediately, no prior working required."""
    state = EscalationState()
    snap, state, _ = advance([agent(status="blocked")], state, now=0.0, cfg=CFG, online=True)
    assert state.waiting_since["a"] == 0.0
    assert snap.views[0].tier == "FRESH"


def test_age_accumulates_across_polls():
    """Age accumulates when agent remains in waiting state."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    snap, state, _ = advance([agent(status="idle")], state, now=300.0, cfg=CFG, online=True)
    assert snap.views[0].age == 300.0
    assert snap.views[0].tier == "MED"


def test_tier_walks_fresh_to_crit():
    """Agent progresses through all tier levels over time."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    seen = []
    for t in (60.0, 300.0, 900.0, 1500.0):
        snap, state, _ = advance([agent(status="idle")], state, now=t, cfg=CFG, online=True)
        seen.append(snap.views[0].tier)
    assert seen == ["FRESH", "MED", "HIGH", "CRIT"]


def test_working_clears_timer_and_rearms():
    """Returning to working clears timer and notified list, enabling re-notification."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    # Transition at time 0, then check at time 700 to reach HIGH
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    _, state, alerts = advance([agent(status="idle")], state, now=700.0, cfg=CFG, online=True)
    assert [a.tier for a in alerts] == ["HIGH"]

    # Agent returns to working
    _, state, _ = advance([agent(status="working")], state, now=800.0, cfg=CFG, online=True)
    assert "a" not in state.waiting_since
    assert state.notified.get("a", []) == []

    # Agent leaves working again; clock re-starts at 800
    _, state, _ = advance([agent(status="idle")], state, now=800.0, cfg=CFG, online=True)
    _, state, alerts = advance([agent(status="idle")], state, now=1500.0, cfg=CFG, online=True)
    assert [a.tier for a in alerts] == ["HIGH"]  # re-armed, fires again


def test_notification_fires_once_per_tier():
    """A given tier notifies only once until re-armed."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    _, state, first = advance([agent(status="idle")], state, now=700.0, cfg=CFG, online=True)
    _, state, second = advance([agent(status="idle")], state, now=800.0, cfg=CFG, online=True)
    assert [a.tier for a in first] == ["HIGH"]
    assert second == []


def test_crit_fires_after_high():
    """CRIT fires only after a prior HIGH notification."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=700.0, cfg=CFG, online=True)
    _, state, alerts = advance([agent(status="idle")], state, now=1300.0, cfg=CFG, online=True)
    assert [a.tier for a in alerts] == ["CRIT"]


def test_fresh_and_med_never_notify():
    """FRESH and MED tiers do not generate notifications."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    for t in (60.0, 300.0, 599.0):
        _, state, alerts = advance([agent(status="idle")], state, now=t, cfg=CFG, online=True)
        assert alerts == []


def test_global_cooldown_suppresses_a_second_agent():
    """Global cooldown allows only one alert per 60-second window."""
    state = EscalationState()
    two = [agent("a", "working"), agent("b", "working")]
    _, state, _ = advance(two, state, now=0.0, cfg=CFG, online=True)
    two = [agent("a", "idle"), agent("b", "idle")]
    _, state, _ = advance(two, state, now=0.0, cfg=CFG, online=True)
    _, state, alerts = advance(two, state, now=700.0, cfg=CFG, online=True)
    assert len(alerts) == 1  # both crossed HIGH; cooldown allows only one


def test_cooldown_expires():
    """After 60 seconds, cooldown expires and the next agent can notify."""
    state = EscalationState()
    two = [agent("a", "working"), agent("b", "working")]
    _, state, _ = advance(two, state, now=0.0, cfg=CFG, online=True)
    two = [agent("a", "idle"), agent("b", "idle")]
    _, state, _ = advance(two, state, now=0.0, cfg=CFG, online=True)
    _, state, first = advance(two, state, now=700.0, cfg=CFG, online=True)
    _, state, second = advance(two, state, now=800.0, cfg=CFG, online=True)
    assert len(first) == 1
    assert len(second) == 1  # 100 s later, cooldown has expired
    assert {a.key for a in first} != {a.key for a in second}


def test_disappearing_agent_is_forgotten():
    """Agents absent from a poll are purged from all state dicts."""
    state = EscalationState()
    _, state, _ = advance([agent()], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([], state, now=100.0, cfg=CFG, online=True)
    assert state.waiting_since == {}
    assert state.notified == {}
    assert state.last_status == {}


def test_blocked_tier_ages_normally():
    """Blocked agents escalate tiers like any other waiting agent."""
    state = EscalationState()
    _, state, _ = advance([agent(status="blocked")], state, now=0.0, cfg=CFG, online=True)
    snap, state, _ = advance([agent(status="blocked")], state, now=700.0, cfg=CFG, online=True)
    assert snap.views[0].tier == "HIGH"


def test_advance_does_not_mutate_input_state():
    """advance() returns a new state and never mutates its input."""
    state = EscalationState()
    advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    assert state.waiting_since == {}
    assert state.last_status == {}


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], "sleeping"),
        (["idle"], "sleeping"),
        (["working", "idle"], "working"),
        (["blocked"], "alarmed"),
        (["working", "blocked"], "alarmed"),
    ],
)
def test_mood_from_statuses_at_zero_age(statuses, expected):
    """Mood is determined by agent statuses and tier levels."""
    agents = [agent(key=str(i), status=s) for i, s in enumerate(statuses)]
    snap, _, _ = advance(agents, EscalationState(), now=0.0, cfg=CFG, online=True)
    assert snap.mood == expected


def test_mood_escalates_with_age():
    """Mood escalates as age increases through tiers."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    moods = []
    for t in (60.0, 300.0, 900.0):
        snap, state, _ = advance([agent(status="idle")], state, now=t, cfg=CFG, online=True)
        moods.append(snap.mood)
    assert moods == ["perked", "alert", "alarmed"]


def test_offline_overrides_every_mood():
    """Offline status overrides all other mood logic."""
    snap, _, _ = advance(
        [agent(status="blocked")], EscalationState(), now=0.0, cfg=CFG, online=False
    )
    assert snap.mood == "offline"


def test_offline_emits_no_alerts():
    """No alerts are emitted when offline, even if thresholds are crossed."""
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    _, _, alerts = advance([agent(status="idle")], state, now=700.0, cfg=CFG, online=False)
    assert alerts == []


def test_views_sort_most_urgent_first():
    """Views are sorted with most urgent (highest tier, oldest age) first."""
    state = EscalationState()
    # Start three agents, all working
    agents = [
        agent("calm", "working"),
        agent("busy", "working"),
        agent("old", "working"),
    ]
    _, state, _ = advance(agents, state, now=0.0, cfg=CFG, online=True)
    # Transition old first at time 0, calm later at time 100
    agents = [agent("calm", "working"), agent("busy", "working"), agent("old", "idle")]
    _, state, _ = advance(agents, state, now=0.0, cfg=CFG, online=True)
    agents = [agent("calm", "idle"), agent("busy", "working"), agent("old", "idle")]
    _, state, _ = advance(agents, state, now=100.0, cfg=CFG, online=True)
    snap, _, _ = advance(agents, state, now=1500.0, cfg=CFG, online=True)
    # old started at 0, calm at 100, so old is older; busy still working
    assert [v.agent.key for v in snap.views] == ["old", "calm", "busy"]


def test_mood_for_is_pure_and_standalone():
    """mood_for is a pure function independent of advance."""
    views = (AgentView(agent=agent(), age=0.0, tier="FRESH"),)
    assert mood_for(views, online=True) == "perked"
    assert mood_for(views, online=False) == "offline"


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (5, "FRESH"),
        (15, "MED"),
        (25, "HIGH"),
        (35, "CRIT"),
    ],
)
def test_tier_with_custom_config(age, expected):
    """Verify tier_for actually reads cfg, not hardcoded values."""
    fast = Config(med_seconds=10, high_seconds=20, crit_seconds=30)
    assert tier_for(age, fast) == expected


def test_tier_differs_between_configs_at_same_age():
    """Ensure custom config genuinely differs from default at the same age."""
    fast = Config(med_seconds=10, high_seconds=20, crit_seconds=30)
    default = Config()
    age = 15
    # Custom config should give MED, default should give FRESH
    assert tier_for(age, fast) == "MED"
    assert tier_for(age, default) == "FRESH"


def test_advance_with_custom_config_thresholds():
    """Verify advance() correctly uses custom config through tier_for."""
    fast = Config(med_seconds=10, high_seconds=20, crit_seconds=30)
    state = EscalationState()
    _, state, _ = advance([agent(status="working")], state, now=0.0, cfg=fast, online=True)
    _, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=fast, online=True)
    tiers = []
    for t in (5.0, 15.0, 25.0):
        snap, state, _ = advance([agent(status="idle")], state, now=t, cfg=fast, online=True)
        tiers.append(snap.views[0].tier)
    assert tiers == ["FRESH", "MED", "HIGH"]


def test_always_idle_agent_produces_no_alerts():
    """An agent that has been idle since startup produces zero alerts after 1300s."""
    state = EscalationState()
    snap, state, alerts = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    # Walk it past all thresholds
    snap, state, alerts = advance([agent(status="idle")], state, now=1300.0, cfg=CFG, online=True)
    assert snap.views[0].tier is None
    assert alerts == []
    assert state.waiting_since == {}


def test_backward_compatibility_missing_last_status():
    """A state without last_status field loads correctly (backward compatibility)."""
    # This is implicitly tested by EscalationState defaulting last_status to {}
    state = EscalationState(
        waiting_since={"a": 100.0},
        notified={"a": ["HIGH"]},
        last_alert_at=50.0,
    )
    assert state.last_status == {}


# Tests for mood_for_session
def test_mood_for_session_returns_session_mood():
    """mood_for_session returns that session's mood, not the aggregate."""
    # Create a snapshot with two sessions: one blocked, one working
    blocked_view = AgentView(agent=agent("blocked_id", "blocked"), age=0.0, tier="FRESH")
    working_view = AgentView(agent=agent("working_id", "working"), age=0.0, tier=None)
    snapshot = Snapshot(views=(blocked_view, working_view), mood="alarmed", online=True)

    # Blocked session should show alarmed
    assert mood_for_session(snapshot, "blocked_id") == "alarmed"
    # Working session should show working
    assert mood_for_session(snapshot, "working_id") == "working"


def test_mood_for_session_unknown_session_sleeping():
    """An unknown session_id yields 'sleeping', NOT 'offline'."""
    blocked_view = AgentView(agent=agent("blocked_id", "blocked"), age=0.0, tier="FRESH")
    snapshot = Snapshot(views=(blocked_view,), mood="alarmed", online=True)

    # Unknown session should be sleeping
    assert mood_for_session(snapshot, "unknown_id") == "sleeping"


def test_mood_for_session_offline_overrides():
    """snapshot.online False yields 'offline' regardless of session state."""
    blocked_view = AgentView(agent=agent("blocked_id", "blocked"), age=0.0, tier="FRESH")
    snapshot = Snapshot(views=(blocked_view,), mood="offline", online=False)

    # Offline should override even a blocked session
    assert mood_for_session(snapshot, "blocked_id") == "offline"


def test_mood_for_session_tier_levels():
    """mood_for_session correctly interprets tier levels."""
    fresh_view = AgentView(agent=agent("fresh_id", "idle"), age=30.0, tier="FRESH")
    med_view = AgentView(agent=agent("med_id", "idle"), age=200.0, tier="MED")
    high_view = AgentView(agent=agent("high_id", "idle"), age=700.0, tier="HIGH")
    crit_view = AgentView(agent=agent("crit_id", "idle"), age=1300.0, tier="CRIT")
    snapshot = Snapshot(
        views=(fresh_view, med_view, high_view, crit_view),
        mood="alarmed",
        online=True,
    )

    assert mood_for_session(snapshot, "fresh_id") == "perked"
    assert mood_for_session(snapshot, "med_id") == "alert"
    assert mood_for_session(snapshot, "high_id") == "alarmed"
    assert mood_for_session(snapshot, "crit_id") == "alarmed"


def test_mood_for_session_status_working():
    """mood_for_session returns 'working' when agent status is working."""
    working_view = AgentView(agent=agent("w", "working"), age=0.0, tier=None)
    idle_view = AgentView(agent=agent("i", "idle"), age=0.0, tier=None)
    snapshot = Snapshot(views=(working_view, idle_view), mood="working", online=True)

    assert mood_for_session(snapshot, "w") == "working"
    assert mood_for_session(snapshot, "i") == "sleeping"


def test_mood_for_session_pure_function():
    """mood_for_session is independent of aggregate mood calculation."""
    # Create a snapshot where aggregate is "alarmed" but one session is sleeping
    blocked_view = AgentView(agent=agent("blocked", "blocked"), age=0.0, tier="FRESH")
    idle_view = AgentView(agent=agent("idle", "idle"), age=0.0, tier=None)
    snapshot = Snapshot(views=(blocked_view, idle_view), mood="alarmed", online=True)

    # Aggregate is alarmed due to blocked session
    assert snapshot.mood == "alarmed"
    # But the idle session's own mood is sleeping
    assert mood_for_session(snapshot, "idle") == "sleeping"


def test_mood_for_session_empty_snapshot():
    """mood_for_session on empty snapshot yields sleeping for any session_id."""
    snapshot = Snapshot(views=(), mood="sleeping", online=True)
    assert mood_for_session(snapshot, "any_id") == "sleeping"


def test_done_on_first_sight_starts_clock():
    """An agent with done status starts the clock immediately, no prior working required.

    This fixes the bug where shellmate installed mid-session, or after a state reset,
    would not escalate a session whose only recorded status is 'done'.
    """
    state = EscalationState()
    snap, state, _ = advance([agent(status="done")], state, now=0.0, cfg=CFG, online=True)
    assert state.waiting_since["a"] == 0.0
    assert snap.views[0].tier == "FRESH"
    # Should escalate to HIGH at 700s like any other waiting agent
    snap, state, _ = advance([agent(status="done")], state, now=700.0, cfg=CFG, online=True)
    assert snap.views[0].tier == "HIGH"


def test_idle_only_does_not_escalate():
    """An 'idle' session never seen working still does NOT escalate, even after a long time.

    This ensures we do not create false positives for idle sessions that have been
    idle since startup (truly ambiguous—we cannot tell if they finished or were just
    never started). The done-status rule only applies to explicit 'done', which the
    Stop hook guarantees means a turn just finished.
    """
    state = EscalationState()
    # Walk an always-idle agent past all thresholds, never having been working
    snap, state, _ = advance([agent(status="idle")], state, now=0.0, cfg=CFG, online=True)
    assert snap.views[0].tier is None
    # 1300 seconds later (well past CRIT threshold of 1200s)
    snap, state, _ = advance([agent(status="idle")], state, now=1300.0, cfg=CFG, online=True)
    assert snap.views[0].tier is None  # Still not escalating
    assert state.waiting_since == {}
    assert snap.mood == "sleeping"  # mood reflects no waiting


def test_advance_preserves_pet_count_and_petted_at():
    """advance() preserves pet_count and petted_at from input state.

    This ensures that the statusline sprite refresh, which calls advance() every 2s,
    does not clobber the pet_count that --pet updates.
    """
    state = EscalationState(pet_count=3, petted_at=123.456)
    snap, new_state, _ = advance([agent(status="working")], state, now=0.0, cfg=CFG, online=True)
    assert new_state.pet_count == 3
    assert new_state.petted_at == 123.456


def test_advance_preserves_pet_count_across_polls():
    """pet_count survives multiple advance() calls without decaying."""
    state = EscalationState(pet_count=5, petted_at=100.0)
    # Simulate multiple statusline refreshes
    for now in (0.0, 2.0, 4.0, 6.0):
        _, state, _ = advance([agent(status="working")], state, now=now, cfg=CFG, online=True)
    assert state.pet_count == 5
    assert state.petted_at == 100.0
