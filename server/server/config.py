from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_EVENT_LOG_PATH = Path("/var/lib/robot-server/events.jsonl")


@dataclass(frozen=True, slots=True)
class Settings:
    robot_id: str = "robot-01"
    robot_token: str = ""
    dashboard_key: str = ""
    session_hours: int = 12
    session_cookie_name: str = "robot_session"
    session_cookie_secure: str = "auto"
    event_log_path: Path = DEFAULT_EVENT_LOG_PATH
    websocket_send_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            robot_id=os.getenv("ROBOT_ID", "robot-01"),
            robot_token=os.getenv("ROBOT_TOKEN", ""),
            dashboard_key=os.getenv("DASHBOARD_KEY", ""),
            session_hours=max(1, int(os.getenv("SESSION_HOURS", "12"))),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "auto").strip().lower(),
            event_log_path=Path(os.getenv("EVENT_LOG_PATH", str(DEFAULT_EVENT_LOG_PATH))),
            websocket_send_timeout=max(1.0, float(os.getenv("WEBSOCKET_SEND_TIMEOUT", "5"))),
        )

    def validate(self) -> None:
        if len(self.robot_token) < 24 or len(self.dashboard_key) < 12:
            raise RuntimeError("ROBOT_TOKEN과 DASHBOARD_KEY를 안전한 값으로 설정해야 합니다.")
        if self.session_cookie_secure not in {"0", "1", "auto"}:
            raise RuntimeError("SESSION_COOKIE_SECURE는 0, 1 또는 auto여야 합니다.")

    def use_secure_cookie(self, request_scheme: str) -> bool:
        return self.session_cookie_secure == "1" or (
            self.session_cookie_secure == "auto" and request_scheme == "https"
        )
