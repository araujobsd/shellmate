"""Desktop notification edge.

notify-send is Linux-only. Shipping only that path would silently give macOS
users a pet with no escalation, which is the one feature justifying the project.
"""

import platform
import subprocess
import sys
from collections.abc import Callable

from shellmate.models import Alert, fmt_age

APP_NAME = "shellmate"


def describe(alert: Alert) -> tuple[str, str]:
    age_str = fmt_age(alert.age)
    if not age_str:
        age_str = "less than a minute"
    return (f"{APP_NAME}: {alert.label}", f"Still waiting after {age_str}")


def command_for(system: str, title: str, body: str) -> list[str] | None:
    if system == "Linux":
        return ["notify-send", "-a", APP_NAME, title, body]
    if system == "Darwin":
        script = f'display notification "{body}" with title "{title}"'
        return ["osascript", "-e", script]
    return None


def _default_runner(cmd: list[str]) -> bool:
    proc = subprocess.run(cmd, capture_output=True, timeout=5.0, check=False)
    return proc.returncode == 0


class Notifier:
    """Fires desktop notifications, disabling itself permanently on first failure."""

    def __init__(
        self,
        system: str | None = None,
        runner: Callable[[list[str]], bool] = _default_runner,
    ) -> None:
        self.system = system or platform.system()
        self._runner = runner
        self.enabled = command_for(self.system, "", "") is not None
        if not self.enabled:
            print(
                f"{APP_NAME}: no notifier for platform {self.system}; notifications off",
                file=sys.stderr,
            )

    def send(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
        title, body = describe(alert)
        cmd = command_for(self.system, title, body)
        if cmd is None:
            self.enabled = False
            return False
        try:
            ok = self._runner(cmd)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"{APP_NAME}: notifier failed ({exc}); notifications off", file=sys.stderr)
            self.enabled = False
            return False
        if not ok:
            print(f"{APP_NAME}: notifier returned non-zero; notifications off", file=sys.stderr)
            self.enabled = False
        return ok
