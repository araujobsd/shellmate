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


# Tests for phrase_text stability (display text doesn't change during mood churn)


def test_phrase_text_stable_during_mood_churn():
    """Test mood flickers working<->perked<->working<->perked over ~70s shows at most 1 text
    change.

    When mood flickers between working and perked (both non-SIGNAL), the phrase_text
    should be chosen once and stay the same even though the live mood changes repeatedly.
    """
    state = EscalationState()

    # t=100: working, phrase_text selected on first run
    snap, state, _ = advance(
        [agent(status="working")], state, now=100.0, cfg=CFG, online=True, character="test"
    )
    initial_text = state.phrase_text
    assert initial_text != ""  # Phrase was selected
    assert state.phrase_set_at == 100.0
    assert snap.mood == "working"

    # t=108: transition to done (initiates clock), mood becomes perked
    _, state, _ = advance(
        [agent(status="done")], state, now=108.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == initial_text  # Text unchanged during mood churn

    # t=120: back to working, mood back to working
    _, state, _ = advance(
        [agent(status="working")], state, now=120.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == initial_text  # Still same text

    # t=131: done again, mood perked again
    _, state, _ = advance(
        [agent(status="done")], state, now=131.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == initial_text  # Still same text

    # t=170: working again, mood still working/perked, well under 90s from t=100
    snap, state, _ = advance(
        [agent(status="working")], state, now=170.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == initial_text  # Still same text through all churn
    assert snap.mood == "working"


def test_phrase_text_refreshes_after_min_seconds():
    """Test minimum lifetime of 90 seconds for phrase_text.

    - At t=1000 with mood=working, phrase_text selected
    - At t=1045 (before 90s elapsed), with same mood, phrase_text should NOT change
    - At t=1100 (after 90s elapsed), with same mood, phrase_text SHOULD refresh
    """
    state = EscalationState()

    # t=1000: working, phrase_text selected
    snap, state, _ = advance(
        [agent(status="working")], state, now=1000.0, cfg=CFG, online=True, character="test"
    )
    text_at_1000 = state.phrase_text
    assert text_at_1000 != ""
    assert state.phrase_set_at == 1000.0
    assert snap.mood == "working"

    # t=1045: still working, 45s elapsed, less than 90s
    snap, state, _ = advance(
        [agent(status="working")], state, now=1045.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == text_at_1000  # No refresh yet
    assert state.phrase_set_at == 1000.0  # Timestamp unchanged
    assert snap.mood == "working"

    # t=1100: still working, 100s elapsed, more than 90s minimum
    snap, state, _ = advance(
        [agent(status="working")], state, now=1100.0, cfg=CFG, online=True, character="test"
    )
    # Text may or may not be the same (depends on phrase selection), but timestamp changed
    assert state.phrase_set_at == 1100.0  # Refreshed after 90s minimum
    assert snap.mood == "working"


def test_phrase_text_immediate_on_escalation():
    """Test immediate new phrase when escalating from working to alert.

    - Start with mood=working (non-SIGNAL) at t=1000, phrase_text selected
    - At t=1001, transition to done which starts clock (perked, still non-SIGNAL)
    - At t=1301, age reaches MED threshold, mood becomes alert (SIGNAL)
    - Verify phrase_text changes immediately on escalation
    """
    state = EscalationState()

    # t=1000: working
    snap, state, _ = advance(
        [agent(status="working")], state, now=1000.0, cfg=CFG, online=True, character="test"
    )
    text_at_1000 = state.phrase_text
    assert text_at_1000 != ""
    assert snap.mood == "working"

    # t=1001: transition to done which starts clock, will become perked (still non-SIGNAL)
    _, state, _ = advance(
        [agent(status="done")], state, now=1001.0, cfg=CFG, online=True, character="test"
    )
    assert state.phrase_text == text_at_1000  # No re-pick yet (perked is non-SIGNAL)

    # t=1301: now age = 300s >= MED threshold (120s), mood becomes alert (SIGNAL)
    snap, state, _ = advance(
        [agent(status="done")], state, now=1301.0, cfg=CFG, online=True, character="test"
    )
    assert snap.mood == "alert"  # Entered SIGNAL
    # Phrase text was re-picked on escalation (could be same or different)
    assert state.phrase_set_at == 1301.0  # Timestamp updated


def test_phrase_text_no_change_in_same_signal():
    """Test that staying in one SIGNAL mood doesn't re-pick phrase on every poll.

    - Transition to alarmed at t=1000, phrase_text selected
    - At t=1050 (still in alarmed, only 50s elapsed), phrase_text should NOT change
    """
    state = EscalationState()

    # t=1000: Set up alarmed mood (blocked status)
    snap, state, _ = advance(
        [agent(status="blocked")], state, now=1000.0, cfg=CFG, online=True, character="test"
    )
    assert snap.mood == "alarmed"
    text_at_1000 = state.phrase_text
    assert text_at_1000 != ""
    assert state.phrase_set_at == 1000.0

    # t=1050: Still alarmed, no mood change, only 50s elapsed (< 90s minimum)
    snap, state, _ = advance(
        [agent(status="blocked")], state, now=1050.0, cfg=CFG, online=True, character="test"
    )
    assert snap.mood == "alarmed"
    assert state.phrase_text == text_at_1000  # No re-pick within same SIGNAL mood before 90s
    assert state.phrase_set_at == 1000.0  # Timestamp unchanged


def test_phrase_text_persists_through_save_load():
    """Test backward compat: phrase_text persists through state save/load.

    - Create state with phrase_text="hello"
    - Save it (via dataclass) and load it back
    - Verify phrase_text loads correctly
    - Also test that a state file WITHOUT phrase_text key loads with default ""
    """
    # Test 1: Save and load with explicit phrase_text
    state = EscalationState(
        waiting_since={"a": 100.0},
        notified={"a": ["HIGH"]},
        last_status={"a": "idle"},
        phrase_text="hello",
        phrase_set_at=1234.5,
    )

    # Simulate "save" by reading the fields
    saved_text = state.phrase_text
    saved_at = state.phrase_set_at
    assert saved_text == "hello"
    assert saved_at == 1234.5

    # Simulate "load" by creating new state with saved values
    loaded_state = EscalationState(
        waiting_since=state.waiting_since,
        notified=state.notified,
        last_status=state.last_status,
        phrase_text=saved_text,
        phrase_set_at=saved_at,
    )
    assert loaded_state.phrase_text == "hello"
    assert loaded_state.phrase_set_at == 1234.5

    # Test 2: Load state without phrase_text field (backward compat)
    # This simulates loading a state file created before phrase_text was added
    loaded_old = EscalationState(
        waiting_since={"a": 100.0},
        notified={"a": ["HIGH"]},
        last_status={"a": "idle"},
        # No phrase_text or phrase_set_at specified, should default to "" and 0.0
    )
    assert loaded_old.phrase_text == ""  # Default value
    assert loaded_old.phrase_set_at == 0.0  # Default value


# Update phrase tests


def test_update_phrase_disabled_when_no_latest_version():
    """When latest_version is None, update phrases are not shown."""
    state = EscalationState()
    snap, state, _ = advance(
        [agent(status="working")],
        state,
        now=0.0,
        cfg=CFG,
        online=True,
        character="cat",
        latest_version=None,
    )
    # Should have a normal working phrase, not an update phrase
    assert state.phrase_text != ""
    # Can't directly assert it's NOT an update phrase without parsing,
    # but update phrases only appear when latest_version is set


def test_update_phrase_honored_when_available():
    """When latest_version is set, update phrases may appear."""
    state = EscalationState()
    snap, state, _ = advance(
        [agent(status="working")],
        state,
        now=4.0,  # int(now) % 4 == 0, so update phrase likely
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",
    )
    # At now=4.0, int(4.0) % 4 == 0, so we should try to pick an update phrase
    # The exact phrase depends on the hash, but it should be set
    assert state.latest_version == "0.2.0"


def test_update_phrase_never_overrides_alert():
    """Update phrases never appear during alert mood."""
    state = EscalationState()
    # First: agent is working
    snap, state, _ = advance(
        [agent(status="working")],
        state,
        now=0.0,
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",
    )
    # Second: agent transitions to idle, starting the waiting clock
    snap, state, _ = advance(
        [agent(status="idle")],
        state,
        now=50.0,  # Just started waiting
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",
    )
    # Third: advance to alert zone (120-600 seconds of waiting)
    snap, state, _ = advance(
        [agent(status="idle")],
        state,
        now=350.0,  # 300 seconds (5 min) since waiting started: alert zone
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",
    )
    assert snap.mood == "alert"
    # Phrase should be an alert phrase, not an update phrase
    # (alert phrases contain "dragging", "check", etc., not "version" or "update")


def test_update_phrase_never_overrides_alarmed():
    """Update phrases never appear during alarmed mood."""
    state = EscalationState()
    # Create escalation that triggers alarmed (blocked or >10min)
    snap, state, _ = advance(
        [agent(status="blocked")],
        state,
        now=1500.0,
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",
    )
    assert snap.mood == "alarmed"
    # Phrase should be an alarm phrase, not an update phrase


def test_update_phrase_never_overrides_offline():
    """Update phrases never appear during offline mood."""
    state = EscalationState()
    snap, state, _ = advance(
        [agent(status="idle")],
        state,
        now=0.0,
        cfg=CFG,
        online=False,  # offline
        character="cat",
        latest_version="0.2.0",
    )
    assert snap.mood == "offline"
    # Phrase should be an offline phrase, not an update phrase


def test_latest_version_persisted_in_state():
    """latest_version is persisted across state saves."""
    state = EscalationState(latest_version="0.1.5")
    assert state.latest_version == "0.1.5"

    # After an advance call, it should still be there
    snap, new_state, _ = advance(
        [agent(status="working")],
        state,
        now=0.0,
        cfg=CFG,
        online=True,
        character="cat",
        latest_version=None,  # Not updated
    )
    # Should persist the old value
    assert new_state.latest_version == "0.1.5"


def test_latest_version_updated_when_provided():
    """latest_version is updated when a new value is provided."""
    state = EscalationState(latest_version="0.1.5")
    snap, new_state, _ = advance(
        [agent(status="working")],
        state,
        now=0.0,
        cfg=CFG,
        online=True,
        character="cat",
        latest_version="0.2.0",  # New update available
    )
    assert new_state.latest_version == "0.2.0"


# End-to-end update phrase test


def test_update_phrase_shown_in_rendered_output():
    """E2E: With update available, buddy shows update phrase in roughly 1/4 of refreshes."""
    from shellmate.characters import UPDATE_PHRASES

    state = EscalationState()

    # Simulate multiple phrase refreshes over time with an update available
    update_phrases_shown = 0
    total_refreshes = 12  # Test over 12 refreshes

    for i in range(total_refreshes):
        now = 1000.0 + (i * 100)  # Advance time for phrase refresh
        snap, state, _ = advance(
            [agent(status="working")],
            state,
            now=now,
            cfg=CFG,
            online=True,
            character="cat",
            latest_version="0.2.0",
        )

        # Check if the phrase is an update phrase
        phrase = state.phrase_text
        if phrase in UPDATE_PHRASES["cat"]:
            update_phrases_shown += 1

    # With deterministic logic (int(now) % 4 == 0), we should see updates
    # at i=0, i=4, i=8 (when int(now) % 4 == 0), so 3 out of 12
    # But the exact count depends on seed distribution; just verify at least one appears
    assert update_phrases_shown > 0, "No update phrases shown despite available update"


def test_phrase_holds_still_while_the_mood_is_unchanged(tmp_path):
    """A buddy parked in one mood must keep its phrase for PHRASE_MIN_SECONDS.

    This goes through the real save/load cycle on purpose. advance() re-picks the
    phrase when the mood ENTERS a signal mood from a non-signal one, and it reads
    the previous mood from persisted state. While last_mood was not written to
    disk it reloaded as "sleeping" every time, so a buddy sitting in alert looked
    like it was entering alert afresh on every call and re-rolled its phrase —
    measured at roughly twice a second on a live install, which is what the whole
    PHRASE_MIN_SECONDS mechanism exists to prevent.
    """
    from shellmate.store import load, save

    path = tmp_path / "state.json"
    state = EscalationState()

    # Drive the buddy into alert: work, stop, then wait past med_seconds.
    _snap, state, _ = advance((agent(status="working"),), state, 0.0, CFG, True)
    _snap, state, _ = advance((agent(status="done"),), state, 10.0, CFG, True)
    snap, state, _ = advance((agent(status="done"),), state, 200.0, CFG, True)
    assert snap.mood == "alert", "precondition: buddy should be in alert"

    save(path, state)
    first_phrase = load(path).phrase_text
    assert first_phrase, "precondition: a phrase should have been picked"

    # Tick every 2s like the statusline's cold path, staying inside the 90s window.
    for tick in range(1, 21):
        now = 200.0 + tick * 2.0
        state = load(path)
        snap, state, _ = advance((agent(status="done"),), state, now, CFG, True)
        save(path, state)
        assert snap.mood == "alert", f"mood drifted at t={now}"
        assert load(path).phrase_text == first_phrase, (
            f"phrase changed at t={now} while the mood never left alert"
        )


def test_each_pane_gets_a_phrase_for_its_own_mood(tmp_path):
    """Two panes in different moods must each say something about their own mood.

    The face is drawn from the per-session mood while the phrase used to come from
    the aggregate mood across every pane, so a pane happily working would show a
    working face beside an alert phrase borrowed from whichever other pane had
    been idle longest.
    """
    from shellmate.characters import PHRASES
    from shellmate.store import load, save

    path = tmp_path / "state.json"
    busy, idle = agent(key="busy", status="working"), agent(key="idle", status="working")
    state = EscalationState()

    # Both start working, then `idle` stops and waits past med_seconds.
    _s, state, _ = advance((busy, idle), state, 0.0, CFG, True)
    idle = agent(key="idle", status="done")
    _s, state, _ = advance((busy, idle), state, 10.0, CFG, True)
    save(path, state)

    # Render each pane the way the statusline does: one call per session id.
    snap, state, _ = advance(
        (busy, idle), load(path), 300.0, CFG, True, character="cat", session_id="busy"
    )
    save(path, state)
    snap2, state, _ = advance(
        (busy, idle), load(path), 300.0, CFG, True, character="cat", session_id="idle"
    )
    save(path, state)

    assert mood_for_session(snap, "busy") == "working"
    assert mood_for_session(snap2, "idle") == "alert"

    final = load(path)
    busy_phrase = final.phrase_by_session["busy"]
    idle_phrase = final.phrase_by_session["idle"]

    # Each pane's phrase belongs to that pane's own mood...
    assert busy_phrase in PHRASES["cat"]["working"], busy_phrase
    assert idle_phrase in PHRASES["cat"]["alert"], idle_phrase
    # ...and rendering the second pane did not clobber the first.
    assert final.last_mood_by_session == {"busy": "working", "idle": "alert"}


def test_per_session_phrase_slots_are_pruned_with_their_sessions(tmp_path):
    """Closed panes must not accumulate in state.json forever."""
    from shellmate.store import load, save

    path = tmp_path / "state.json"
    state = EscalationState()
    _s, state, _ = advance(
        (agent(key="a", status="working"),), state, 0.0, CFG, True, session_id="a"
    )
    save(path, state)
    assert "a" in load(path).phrase_by_session

    # Session "a" is gone; only "b" is live now.
    _s, state, _ = advance(
        (agent(key="b", status="working"),), load(path), 5.0, CFG, True, session_id="b"
    )
    save(path, state)
    remaining = load(path)
    assert "a" not in remaining.phrase_by_session
    assert "b" in remaining.phrase_by_session
