"""Event log data structures for match-level simulation output."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Event:
    minute: int
    team: str
    event_type: str
    zone: str
    success: bool = True
    xg: float = 0.0
    notes: Optional[str] = None


@dataclass
class EventLog:
    events: list[Event] = field(default_factory=list)

    def add(self, event: Event) -> None:
        self.events.append(event)

    def __len__(self) -> int:
        return len(self.events)
