from __future__ import annotations

import asyncio
from typing import Any


class OutboundBuffer:
    """Bounded priority buffer with latest-only video and telemetry semantics."""

    def __init__(self, normal_size: int = 10, priority_size: int = 20) -> None:
        self.normal: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=normal_size)
        self.priority: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=priority_size)
        self.ready = asyncio.Event()

    @staticmethod
    def is_priority(event: dict[str, Any]) -> bool:
        return event.get("type") in {"command_result", "status"}

    def put(self, event: dict[str, Any]) -> None:
        if self.is_priority(event):
            self.put_priority(self.priority, event)
        else:
            self.put_normal(self.normal, event)
        self.ready.set()

    @staticmethod
    def put_priority(queue: asyncio.Queue, event: dict[str, Any]) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.task_done()
                queue.put_nowait(event)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                print("중요 원격 이벤트 큐가 가득 찼습니다.")

    @staticmethod
    def put_normal(queue: asyncio.Queue, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        replace_stream_frame = event_type == "camera" and bool(event.get("stream"))
        replace_telemetry = event_type == "telemetry"
        if replace_stream_frame or replace_telemetry:
            retained = []
            while True:
                try:
                    queued = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                queue.task_done()
                same_stream = (
                    replace_stream_frame
                    and queued.get("type") == "camera"
                    and bool(queued.get("stream"))
                )
                same_telemetry = replace_telemetry and queued.get("type") == "telemetry"
                if not same_stream and not same_telemetry:
                    retained.append(queued)
            for queued in retained:
                queue.put_nowait(queued)
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            if event.get("type") != "telemetry":
                print("원격 전송 큐가 가득 찼습니다.")

    async def get(self) -> tuple[asyncio.Queue, dict[str, Any]]:
        while True:
            try:
                return self.priority, self.priority.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                return self.normal, self.normal.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self.ready.clear()
            if not self.priority.empty() or not self.normal.empty():
                self.ready.set()
                continue
            await self.ready.wait()
