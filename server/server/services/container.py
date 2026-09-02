from __future__ import annotations

from dataclasses import dataclass

from server.config import Settings
from server.services.event_log import EventLog
from server.services.robot_hub import RobotHub
from server.services.sessions import SessionStore


@dataclass(slots=True)
class AppServices:
    settings: Settings
    sessions: SessionStore
    event_log: EventLog
    hub: RobotHub

    @classmethod
    def build(cls, settings: Settings) -> "AppServices":
        sessions = SessionStore(settings.session_hours)
        event_log = EventLog(settings.event_log_path)
        hub = RobotHub(settings, event_log)
        return cls(settings=settings, sessions=sessions, event_log=event_log, hub=hub)
