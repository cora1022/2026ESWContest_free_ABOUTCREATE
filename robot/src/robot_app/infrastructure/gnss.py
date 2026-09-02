from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any

from robot_app.config import GnssSettings, RobotSettings


class GnssReader:
    """Keep the latest gpsd TPV fix without blocking robot control."""

    def __init__(self, settings: GnssSettings | None = None) -> None:
        self.settings = settings or RobotSettings.from_env().gnss
        self.enabled = self.settings.enabled
        self.host = self.settings.host
        self.port = self.settings.port
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._latest: dict[str, Any] | None = None

    def start(self) -> None:
        if not self.enabled or (self._thread and self._thread.is_alive()):
            return
        self._thread = threading.Thread(target=self._run, name="gnss-reader", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._latest) if self._latest else None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=3.0) as connection:
                    connection.settimeout(5.0)
                    stream = connection.makefile("r", encoding="utf-8", errors="replace")
                    connection.sendall(b'?WATCH={"enable":true,"json":true};\n')
                    for line in stream:
                        if self._stop.is_set():
                            return
                        self._consume(line)
            except OSError as exc:
                print(f"GNSS gpsd 연결 대기 중: {exc}")
                self._stop.wait(5.0)

    def _consume(self, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return
        if payload.get("class") != "TPV" or int(payload.get("mode") or 0) < 2:
            return
        if "lat" not in payload or "lon" not in payload:
            return
        fix = {
            "latitude": float(payload["lat"]),
            "longitude": float(payload["lon"]),
            "speed_mps": float(payload.get("speed") or 0.0),
            "track_deg": float(payload.get("track") or 0.0),
            "fix_time": payload.get("time"),
            "received_at": time.time(),
        }
        with self._lock:
            self._latest = fix
