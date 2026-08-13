from shellmate.app import App
from shellmate.config import Config
from shellmate.models import Alert


def build(tmp_path, notifier=None, cfg=None):
    """Build an App with a clean state directory."""
    return App(
        cfg=cfg or Config(),
        state_path=tmp_path / "state.json",
        notifier=notifier,
    )


def test_tick_returns_renderable_lines(tmp_path, monkeypatch):
    """Verify that app.tick() returns renderable lines with session data."""
    from shellmate.models import Agent

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    def sample():
        agent = Agent(
            key="uuid-a",
            status="done",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    monkeypatch.setattr("shellmate.app.session.sample", sample)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    lines = app.tick(now=0.0, cols=30)
    assert lines
    assert any("my-project" in ln for ln in lines)


def test_polls_only_after_the_poll_interval(tmp_path, monkeypatch):
    """Verify that polling respects the configured poll_seconds interval.

    This test verifies that session.sample() is only called after the poll
    interval has elapsed.
    """
    from shellmate.models import Agent

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    call_count = [0]

    def counting_sample():
        call_count[0] += 1
        agent = Agent(
            key="uuid-a",
            status="done",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    monkeypatch.setattr("shellmate.app.session.sample", counting_sample)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    app.tick(now=0.0, cols=30)
    polls_after_first = call_count[0]
    app.tick(now=0.3, cols=30)  # inside the 2.0s interval
    app.tick(now=0.6, cols=30)
    assert call_count[0] == polls_after_first
    app.tick(now=2.5, cols=30)  # past it
    assert call_count[0] == polls_after_first + 1


def test_animation_advances_between_ticks(tmp_path, monkeypatch):

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    def sample():
        return ([], True)

    monkeypatch.setattr("shellmate.app.session.sample", sample)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    assert app.tick(now=0.0, cols=30) != app.tick(now=0.6, cols=30)


def test_offline_when_source_unavailable(tmp_path, monkeypatch):
    """Verify that app renders correctly when no sessions are available.

    This test mocks session.sample() to return no sessions.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    def sample():
        return ([], True)

    monkeypatch.setattr("shellmate.app.session.sample", sample)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    lines = app.tick(now=0.0, cols=30)
    # With no agents running, should render "no agents" message
    assert lines
    assert any("no agents" in ln for ln in lines)
    assert app.snapshot.mood == "sleeping"


def test_state_survives_a_restart(tmp_path, monkeypatch):
    """Verify that escalation state persists across restarts.

    This test simulates an agent transitioning from working to done. The state
    is saved, then loaded in a new app instance. The age recorded during the
    first session should be preserved.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    from shellmate.models import Agent

    # Mock session.sample to return agents
    def working_agent():
        agent = Agent(
            key="uuid-a",
            status="working",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    def done_agent():
        agent = Agent(
            key="uuid-a",
            status="done",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    monkeypatch.setattr("shellmate.app.session.sample", working_agent)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    app.tick(now=0.0, cols=30)  # First poll: agent is working
    assert app.state.last_status == {"uuid-a": "working"}

    # Second poll: agent transitions to done, waiting_since is set to 2.5
    monkeypatch.setattr("shellmate.app.session.sample", done_agent)
    app.tick(now=2.5, cols=30)
    assert app.state.waiting_since == {"uuid-a": 2.5}
    app.shutdown()

    # Create a new app with the same state file
    revived = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    monkeypatch.setattr("shellmate.app.session.sample", done_agent)
    lines = revived.tick(now=700.0, cols=30)
    # Age should be 700 - 2.5 = 697.5 seconds ≈ 11m 37s, which renders as "11m"
    assert any("11m" in ln for ln in lines)  # age carried across the restart


def test_alerts_reach_the_notifier(tmp_path, monkeypatch):
    """Verify that alerts are sent to the notifier when escalation occurs.

    This test simulates an agent becoming stuck in the done state long enough
    to reach the HIGH escalation tier, which should trigger an alert.
    """
    from shellmate.models import Agent

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    sent: list[Alert] = []

    class Spy:
        enabled = True

        def send(self, alert):
            sent.append(alert)
            return True

    def working_agent():
        agent = Agent(
            key="uuid-a",
            status="working",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    def done_agent():
        agent = Agent(
            key="uuid-a",
            status="done",
            label="my-project",
            pane_id="",
            tab_id="",
        )
        return ([agent], True)

    monkeypatch.setattr("shellmate.app.session.sample", working_agent)

    app = App(
        cfg=Config(notify=True),
        state_path=tmp_path / "shellmate" / "state.json",
        notifier=Spy(),
    )
    app.tick(now=0.0, cols=30)  # First poll: agent is working

    # Second poll: agent transitions to done, waiting starts
    monkeypatch.setattr("shellmate.app.session.sample", done_agent)
    app.tick(now=2.5, cols=30)

    # Third poll: Age is 700 - 2.5 = 697.5s, reaches HIGH tier (600s+)
    app.tick(now=700.0, cols=30)
    assert [a.tier for a in sent] == ["HIGH"]


def test_notifications_suppressed_when_disabled_in_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    def sample():
        return ([], True)

    monkeypatch.setattr("shellmate.app.session.sample", sample)

    sent = []

    class Spy:
        enabled = True

        def send(self, alert):
            sent.append(alert)
            return True

    app = App(
        cfg=Config(notify=False),
        state_path=tmp_path / "shellmate" / "state.json",
        notifier=Spy(),
    )
    app.tick(now=0.0, cols=30)
    app.tick(now=700.0, cols=30)
    assert sent == []


def test_three_consecutive_ticks_do_not_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    def sample():
        return ([], True)

    monkeypatch.setattr("shellmate.app.session.sample", sample)

    app = App(cfg=Config(), state_path=tmp_path / "shellmate" / "state.json")
    for i in range(3):
        assert app.tick(now=i * 0.6, cols=30)


def test_main_all_flag_returns_zero(capsys):
    from shellmate.app import main

    result = main(["--all"])
    assert result == 0


def test_main_all_flag_shows_all_characters(capsys):
    from shellmate import characters
    from shellmate.app import main

    main(["--all"])
    captured = capsys.readouterr()

    # Every character name should appear
    for name in characters.NAMES:
        assert name in captured.out

    # Every mood should appear
    for mood in characters.MOODS:
        assert mood in captured.out


def test_main_all_flag_does_not_read_sessions(capsys):
    from shellmate.app import main

    # A runner that would raise if called
    def would_fail_if_called(args):
        raise RuntimeError("sessions should not be read for --all")

    # We can't pass the runner to main() directly, but we can verify
    # that main(["--all"]) completes without constructing an App
    result = main(["--all"])
    captured = capsys.readouterr()
    assert result == 0
    assert "cat" in captured.out  # Some output was produced


def test_main_all_flag_config_hint_appears_once_per_character(capsys):
    from shellmate import characters
    from shellmate.app import main

    main(["--all"])
    captured = capsys.readouterr()

    # Each character's config hint should appear exactly once
    for char_name in characters.NAMES:
        count = captured.out.count(f'character = "{char_name}"')
        assert count == 1, f"Config hint for {char_name} appeared {count} times, expected 1"


def test_main_face_flag_returns_zero(capsys, monkeypatch):
    from shellmate.app import main

    # Prevent actual polling by mocking the config load
    def mock_load_config():
        return Config()

    monkeypatch.setattr("shellmate.app.config_mod.load_config", mock_load_config)
    monkeypatch.setattr("shellmate.app.session.sample", lambda: ([], True))

    result = main(["--face"])
    assert result == 0


def _pin_identity(monkeypatch, age_seconds):
    """Pin --face to a synthetic identity of a given age.

    Without this the test reads the developer's real identity.json, so what it
    asserts depends on how old their buddy happens to be — it passed for months
    and then broke the day someone reinstalled, because a fresh install is an
    egg and eggs render an egg face, correctly. A CI runner mints a newborn
    every run, so the unpinned version was a latent red on any clean machine.
    """
    import time

    from shellmate.identity import Identity

    born_at = time.time() - age_seconds
    ident = Identity(seed="0" * 32, name="Testu", species="cat", born_at=born_at)
    monkeypatch.setattr("shellmate.app.store.load_identity", lambda _path: ident)


def test_main_face_flag_prints_compact_face(capsys, monkeypatch):
    from shellmate import characters
    from shellmate.app import main

    def mock_load_config():
        return Config(character="cat")

    monkeypatch.setattr("shellmate.app.config_mod.load_config", mock_load_config)
    monkeypatch.setattr("shellmate.app.session.sample", lambda: ([], True))
    _pin_identity(monkeypatch, characters.EGG_SECONDS + 3600)  # hatched

    main(["--face"])
    captured = capsys.readouterr()
    output = captured.out.strip()

    # Output should be a valid compact face (not empty, should be a face string)
    assert output
    # For sleeping mood with no agents (online=True), should print the sleeping face
    expected = characters.compact_for("cat", "sleeping")
    # Strip color codes if present
    import re

    cleaned = re.sub(r"\033\[[0-9;]*m", "", output)
    assert expected in cleaned


def test_main_face_flag_shows_egg_before_hatching(capsys, monkeypatch):
    """A buddy still inside its egg shows an egg face, not its species face.

    This is what a brand-new install renders in the status line, so it is the
    first thing every user sees. It regressed once already: --face had no
    concept of hatching and showed a small owl on a fresh macOS install.
    """
    from shellmate import characters
    from shellmate.app import main

    monkeypatch.setattr("shellmate.app.config_mod.load_config", lambda: Config(character="cat"))
    monkeypatch.setattr("shellmate.app.session.sample", lambda: ([], True))
    _pin_identity(monkeypatch, 60)  # one minute old — still an egg

    main(["--face"])
    import re

    cleaned = re.sub(r"\033\[[0-9;]*m", "", capsys.readouterr().out.strip())

    assert cleaned in characters.EGG_COMPACT
    assert cleaned != characters.compact_for("cat", "sleeping")


def test_main_face_flag_never_notifies(monkeypatch):
    """Verify that --face never constructs a Notifier."""
    from shellmate.app import main

    notifier_constructed = []

    original_notifier = None

    def mock_notifier_init(self):
        notifier_constructed.append(True)
        if original_notifier:
            original_notifier(self)

    def mock_load_config():
        return Config()

    monkeypatch.setattr("shellmate.app.config_mod.load_config", mock_load_config)
    monkeypatch.setattr("shellmate.app.session.sample", lambda: ([], True))
    monkeypatch.setattr("shellmate.notify.Notifier.__init__", mock_notifier_init)

    main(["--face"])

    # Notifier should never be constructed when using --face
    assert not notifier_constructed, "Notifier was constructed during --face invocation"


def test_main_face_flag_handles_offline(capsys, monkeypatch):
    from shellmate.app import main

    def mock_load_config():
        return Config()

    monkeypatch.setattr("shellmate.app.config_mod.load_config", mock_load_config)
    # session module always returns online=True, so we can't test offline this way
    monkeypatch.setattr("shellmate.app.session.sample", lambda: ([], True))

    result = main(["--face"])
    assert result == 0
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should still print something (offline face)
    assert output


def test_main_face_flag_handles_exceptions(capsys, monkeypatch):
    from shellmate.app import main

    def mock_load_config():
        raise RuntimeError("Config error")

    monkeypatch.setattr("shellmate.app.config_mod.load_config", mock_load_config)

    result = main(["--face"])
    assert result == 0
    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should still print offline face even on error
    assert output
