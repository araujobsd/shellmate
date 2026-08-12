from shellmate.models import Alert
from shellmate.notify import Notifier, command_for, describe

ALERT = Alert(key="a", label="backend", tier="HIGH", age=700.0)


def test_linux_uses_notify_send():
    cmd = command_for("Linux", "t", "b")
    assert cmd[0] == "notify-send"
    assert "t" in cmd and "b" in cmd


def test_macos_uses_osascript():
    cmd = command_for("Darwin", "t", "b")
    assert cmd[0] == "osascript"
    assert any("display notification" in part for part in cmd)


def test_unsupported_platform_has_no_command():
    assert command_for("Windows", "t", "b") is None


def test_describe_mentions_label_and_age():
    title, body = describe(ALERT)
    assert "backend" in title + body
    assert "11m" in body
    assert "waiting" in body
    assert "blocked" not in body


def test_describe_uses_fmt_age_formatting():
    # 3700s should be "1h", not "61m" — validates shared formatting
    alert = Alert(key="a", label="test", tier="MED", age=3700.0)
    title, body = describe(alert)
    assert "1h" in body
    assert "61m" not in body


def test_describe_handles_durations_under_60s():
    alert = Alert(key="a", label="test", tier="MED", age=30.0)
    title, body = describe(alert)
    assert "less than a minute" in body


def test_notifier_is_disabled_on_unsupported_platform():
    n = Notifier(system="Windows", runner=lambda cmd: True)
    assert n.enabled is False
    assert n.send(ALERT) is False


def test_notifier_invokes_the_runner():
    calls = []
    n = Notifier(system="Linux", runner=lambda cmd: calls.append(cmd) or True)
    assert n.send(ALERT) is True
    assert len(calls) == 1
    assert calls[0][0] == "notify-send"


def test_notifier_disables_itself_after_a_failure():
    def boom(cmd):
        raise OSError("no such binary")

    n = Notifier(system="Linux", runner=boom)
    assert n.send(ALERT) is False
    assert n.enabled is False


def test_disabled_notifier_stops_calling_the_runner():
    calls = []

    def flaky(cmd):
        calls.append(cmd)
        raise OSError("gone")

    n = Notifier(system="Linux", runner=flaky)
    n.send(ALERT)
    n.send(ALERT)
    n.send(ALERT)
    assert len(calls) == 1  # only the first attempt runs


def test_runner_returning_false_also_disables():
    n = Notifier(system="Linux", runner=lambda cmd: False)
    assert n.send(ALERT) is False
    assert n.enabled is False
