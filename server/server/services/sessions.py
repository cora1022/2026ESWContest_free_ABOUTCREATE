from __future__ import annotations

import secrets
import time


class SessionStore:
    def __init__(self, session_hours: int) -> None:
        self._session_seconds = session_hours * 3600
        self._sessions: dict[str, float] = {}

    def create(self) -> tuple[str, float]:
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + self._session_seconds
        self._sessions[token] = expires_at
        self.cleanup()
        return token, expires_at

    def valid(self, token: str) -> bool:
        expires_at = self._sessions.get(token, 0)
        if expires_at <= time.time():
            self._sessions.pop(token, None)
            return False
        return True

    def expires_at(self, token: str) -> float | None:
        return self._sessions.get(token)

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)

    def cleanup(self) -> None:
        now = time.time()
        for token, expires_at in list(self._sessions.items()):
            if expires_at <= now:
                self._sessions.pop(token, None)

    @property
    def sessions(self) -> dict[str, float]:
        """Read-only compatibility view for existing diagnostics."""
        return self._sessions
