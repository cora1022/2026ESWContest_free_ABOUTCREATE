from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from pathlib import Path
from typing import Any


class EventLog:
    def __init__(self, path: Path, max_events: int = 100) -> None:
        self.path = path
        self.events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._write_lock = asyncio.Lock()

    async def append(self, event: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        safe_event = dict(event)
        safe_event.pop("image_b64", None)
        safe_event.pop("audio_b64", None)
        safe_event.pop("binary_payload", None)
        safe_event.setdefault("server_time", time.time())
        self.events.appendleft(safe_event)
        if persist:
            try:
                async with self._write_lock:
                    await asyncio.to_thread(self._append_line, safe_event)
            except OSError as exc:
                print(f"이벤트 로그 저장 실패: {exc}")
        return safe_event

    def latest(self, limit: int = 30) -> list[dict[str, Any]]:
        return list(self.events)[:limit]

    def _append_line(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
