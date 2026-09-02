from __future__ import annotations

import asyncio
import copy
import time
from collections import deque
from contextlib import suppress
from typing import Any

from fastapi import HTTPException, WebSocket

from server.config import Settings
from server.services.event_log import EventLog


class DashboardPeer:
    """Non-blocking sender with a bounded event queue and coalesced camera frame."""

    def __init__(
        self,
        hub: "RobotHub",
        websocket: WebSocket,
        session_token: str,
        *,
        max_events: int = 32,
    ) -> None:
        self.hub = hub
        self.websocket = websocket
        self.session_token = session_token
        self.max_events = max_events
        self.events: deque[dict[str, Any]] = deque()
        self.latest_frame: bytes | None = None
        self.wake = asyncio.Event()
        self.closed = asyncio.Event()
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.task = asyncio.create_task(self._sender(), name="dashboard-sender")

    def offer_event(self, event: dict[str, Any]) -> bool:
        if self.closed.is_set() or len(self.events) >= self.max_events:
            return False
        self.events.append(copy.deepcopy(event))
        self.wake.set()
        return True

    def offer_frame(self, payload: bytes) -> None:
        if self.closed.is_set():
            return
        self.latest_frame = payload
        self.wake.set()

    async def stop(
        self,
        *,
        close_socket: bool,
        code: int = 1000,
        reason: str = "dashboard disconnected",
    ) -> None:
        self.closed.set()
        self.wake.set()
        if self.task and self.task is not asyncio.current_task():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if close_socket:
            with suppress(Exception):
                await asyncio.wait_for(
                    self.websocket.close(code=code, reason=reason),
                    timeout=self.hub.settings.websocket_send_timeout,
                )

    async def _sender(self) -> None:
        try:
            while not self.closed.is_set():
                await self.wake.wait()
                self.wake.clear()

                event = self.events.popleft() if self.events else None
                if event is not None:
                    await asyncio.wait_for(
                        self.websocket.send_json(event),
                        timeout=self.hub.settings.websocket_send_timeout,
                    )

                frame = self.latest_frame
                self.latest_frame = None
                if frame is not None:
                    await asyncio.wait_for(
                        self.websocket.send_bytes(frame),
                        timeout=self.hub.settings.websocket_send_timeout,
                    )

                if self.events or self.latest_frame is not None:
                    self.wake.set()
        except asyncio.CancelledError:
            raise
        except Exception:
            await self.hub.remove_dashboard(
                self.websocket,
                close_socket=True,
                code=1011,
                reason="dashboard send failed",
            )
        finally:
            self.closed.set()


class RobotHub:
    def __init__(self, settings: Settings, event_log: EventLog) -> None:
        self.settings = settings
        self.event_log = event_log
        self.robot: WebSocket | None = None
        self.robot_send_lock = asyncio.Lock()
        self.robot_lifecycle_lock = asyncio.Lock()
        self.dashboard_peers: dict[WebSocket, DashboardPeer] = {}
        self.state = self._offline_state()
        self.locations: deque[dict[str, Any]] = deque(maxlen=500)
        self.camera_image: bytes | None = None
        self.camera_time: float | None = None

    def _offline_state(self) -> dict[str, Any]:
        return {
            "robot_id": self.settings.robot_id,
            "online": False,
            "last_seen": None,
            "mode": "OFFLINE",
            "motion": "STOPPED",
            "video_active": False,
            "location": None,
        }

    @property
    def events(self):
        """Compatibility view retained for existing diagnostics."""
        return self.event_log.events

    @property
    def dashboards(self) -> set[WebSocket]:
        """Compatibility view of currently registered dashboard sockets."""
        return set(self.dashboard_peers)

    async def send_command(self, command: dict[str, Any]) -> None:
        robot = self.robot
        if robot is None:
            raise HTTPException(status_code=503, detail="로봇이 VPS에 연결되어 있지 않습니다.")
        try:
            async with self.robot_send_lock:
                await asyncio.wait_for(
                    robot.send_json(command),
                    timeout=self.settings.websocket_send_timeout,
                )
        except Exception as exc:
            await self.disconnect_robot(
                robot,
                close_socket=True,
                code=1011,
                reason="command send failed",
            )
            raise HTTPException(status_code=503, detail="로봇 연결이 끊겼습니다.") from exc

    async def replace_robot(self, websocket: WebSocket) -> None:
        async with self.robot_lifecycle_lock:
            previous = self.robot
            self.robot = websocket
            self.state.clear()
            self.state.update(self._offline_state())
            self.state.update({"online": True, "last_seen": time.time()})
            self.camera_image = None
            self.camera_time = None
        if previous and previous is not websocket:
            with suppress(Exception):
                await asyncio.wait_for(
                    previous.close(code=1012, reason="replaced by new robot connection"),
                    timeout=self.settings.websocket_send_timeout,
                )

    async def disconnect_robot(
        self,
        websocket: WebSocket,
        *,
        close_socket: bool,
        code: int = 1000,
        reason: str = "robot disconnected",
    ) -> bool:
        async with self.robot_lifecycle_lock:
            if self.robot is not websocket:
                return False
            self.robot = None
            self.state.clear()
            self.state.update(self._offline_state())
            self.camera_image = None
            self.camera_time = None

        if close_socket:
            with suppress(Exception):
                await asyncio.wait_for(
                    websocket.close(code=code, reason=reason),
                    timeout=self.settings.websocket_send_timeout,
                )
        await self.record(
            {
                "type": "robot_disconnected",
                "robot_id": self.settings.robot_id,
                "reason": reason,
            }
        )
        await self.broadcast({"type": "state", "state": self.state})
        return True

    def add_dashboard(self, websocket: WebSocket, session_token: str) -> DashboardPeer:
        peer = DashboardPeer(self, websocket, session_token)
        self.dashboard_peers[websocket] = peer
        peer.start()
        return peer

    async def remove_dashboard(
        self,
        websocket: WebSocket,
        *,
        close_socket: bool,
        code: int = 1000,
        reason: str = "dashboard disconnected",
    ) -> None:
        peer = self.dashboard_peers.pop(websocket, None)
        if peer is None:
            return
        await peer.stop(close_socket=close_socket, code=code, reason=reason)

    async def close_dashboards_for_session(self, session_token: str, *, reason: str) -> None:
        peers = [
            peer
            for peer in list(self.dashboard_peers.values())
            if peer.session_token == session_token
        ]
        if not peers:
            return
        await asyncio.gather(
            *(
                self.remove_dashboard(
                    peer.websocket,
                    close_socket=True,
                    code=1008,
                    reason=reason,
                )
                for peer in peers
            )
        )

    async def broadcast(self, event: dict[str, Any]) -> None:
        for peer in list(self.dashboard_peers.values()):
            if not peer.offer_event(event):
                asyncio.create_task(
                    self.remove_dashboard(
                        peer.websocket,
                        close_socket=True,
                        code=1013,
                        reason="dashboard queue full",
                    )
                )

    async def broadcast_bytes(self, payload: bytes) -> None:
        for peer in list(self.dashboard_peers.values()):
            peer.offer_frame(payload)

    async def record(
        self,
        event: dict[str, Any],
        *,
        persist: bool = True,
        broadcast_event: bool = True,
    ) -> dict[str, Any]:
        safe_event = await self.event_log.append(event, persist=persist)
        if broadcast_event:
            await self.broadcast({"type": "event", "event": safe_event})
        return safe_event

    async def shutdown(self) -> None:
        peers = list(self.dashboard_peers.values())
        if peers:
            await asyncio.gather(
                *(
                    self.remove_dashboard(peer.websocket, close_socket=False)
                    for peer in peers
                )
            )
        robot = self.robot
        if robot is not None:
            await self.disconnect_robot(
                robot,
                close_socket=True,
                code=1001,
                reason="server shutdown",
            )
