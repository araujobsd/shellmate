"""Value types shared across modules. No behaviour, no I/O."""

from dataclasses import dataclass, field


def fmt_age(seconds: float) -> str:
    """Format seconds as a human-readable age. Returns '' for durations under 60s."""
    if seconds < 60:
        return ""
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    return f"{int(minutes // 60)}h"


@dataclass(frozen=True)
class Agent:
    key: str  # agent_session.value — stable across polls, unlike pane_id
    status: str  # working | done | blocked | idle | unknown
    label: str  # tab label if resolvable, else basename(cwd)
    pane_id: str
    tab_id: str


@dataclass(frozen=True)
class AgentView:
    agent: Agent
    age: float  # seconds spent waiting; 0.0 when not waiting
    tier: str | None  # FRESH | MED | HIGH | CRIT, or None when not waiting


@dataclass(frozen=True)
class Snapshot:
    views: tuple[AgentView, ...]
    mood: str
    online: bool


@dataclass(frozen=True)
class Alert:
    key: str
    label: str
    tier: str
    age: float


@dataclass
class EscalationState:
    waiting_since: dict[str, float] = field(default_factory=dict)
    notified: dict[str, list[str]] = field(default_factory=dict)
    last_alert_at: float = 0.0
    last_status: dict[str, str] = field(default_factory=dict)
    petted_at: float | None = None  # timestamp of last petting
    pet_count: int = 0  # total number of times petted
    last_mood: str = "sleeping"  # previous mood (to detect mood changes)
    mood_since: float = 0.0  # timestamp when current mood was entered (for stable phrases)
    phrase_text: str = ""  # the rendered phrase to display
    phrase_set_at: float = 0.0  # when phrase_text was chosen
    latest_version: str | None = None  # newest version available, if known
