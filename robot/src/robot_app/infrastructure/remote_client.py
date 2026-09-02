from __future__ import annotations

import asyncio
import json
import random
import ssl
import threading
from typing import Any

from robot_protocol.messages import HelloAckMessage, HelloMessage
from robot_protocol.transport import pack_binary_event
from robot_protocol.version import PROTOCOL_VERSION
from websockets.asyncio.client import connect

from robot_app.config import RemoteSettings, RobotSettings
from robot_app.infrastructure.outbound_buffer import OutboundBuffer


class RobotRemoteClient:
    def __init__(self, controller, settings: RemoteSettings | None = None) -> None:
        self.controller = controller
        self.settings = settings or RobotSettings.from_env().remote
        self.url = self.settings.server_url
        self.robot_id = self.settings.robot_id
        self.robot_token = self.settings.robot_token
        self.enabled = self.settings.enabled
        self.telemetry_interval = self.settings.telemetry_interval_sec
        self.send_timeout = self.settings.send_timeout_sec
        self.handshake_timeout = self.settings.handshake_timeout_sec
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._buffer: OutboundBuffer | None = None

    def start(self) -> None:
        if not self.enabled:
            print("원격 서버 연결이 비활성화되었습니다. 로컬 모드로 실행합니다.")
            return
        if not self.robot_token:
            print("ROBOT_TOKEN이 없어 원격 연결을 시작하지 않습니다.")
            return
        if self.url.startswith("ws://") and not self.settings.allow_insecure_server:
            print("안전하지 않은 ws:// 연결은 차단했습니다. wss://를 사용하세요.")
            return
        self.controller.set_event_listener(self.publish)
        self._thread = threading.Thread(target=self._thread_main, name="vps-websocket", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._loop:
            self._loop.call_soon_threadsafe(lambda: None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self.controller.set_event_listener(None)

    def publish(self, event: dict[str, Any]) -> None:
        loop = self._loop
        buffer = self._buffer
        if not loop or not buffer or loop.is_closed():
            return
        loop.call_soon_threadsafe(buffer.put, event)

    @staticmethod
    def _is_priority_event(event: dict[str, Any]) -> bool:
        return OutboundBuffer.is_priority(event)

    @staticmethod
    def _put_priority_event(outgoing: asyncio.Queue, event: dict[str, Any]) -> None:
        OutboundBuffer.put_priority(outgoing, event)

    @staticmethod
    def _put_event(outgoing: asyncio.Queue, event: dict[str, Any]) -> None:
        OutboundBuffer.put_normal(outgoing, event)

    def _thread_main(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._buffer = OutboundBuffer()
        delay = 1.0
        while not self._stop.is_set():
            try:
                ssl_context = ssl.create_default_context() if self.url.startswith("wss://") else None
                async with connect(
                    self.url,
                    ssl=ssl_context,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=3_000_000,
                ) as websocket:
                    await self._run_connected_session(websocket)
                    delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"VPS 연결 실패, {delay:.0f}초 후 재시도: {exc}")
            finally:
                self.controller.set_remote_connected(False)
            if self._stop.is_set():
                break
            await asyncio.sleep(delay + random.random())
            delay = min(delay * 2, 30.0)

    async def _perform_handshake(self, websocket) -> HelloAckMessage:
        hello = HelloMessage(
            robot_id=self.robot_id,
            token=self.robot_token,
            protocol_version=PROTOCOL_VERSION,
        )
        await asyncio.wait_for(
            websocket.send(json.dumps(hello.to_dict(), ensure_ascii=False)),
            timeout=self.send_timeout,
        )
        try:
            raw_ack = await asyncio.wait_for(
                websocket.recv(),
                timeout=self.handshake_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise ConnectionError(
                f"서버 hello_ack가 {self.handshake_timeout:.1f}초 안에 도착하지 않았습니다."
            ) from exc
        try:
            payload = json.loads(raw_ack)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ConnectionError("서버 hello_ack가 올바른 JSON이 아닙니다.") from exc
        if not isinstance(payload, dict):
            raise ConnectionError("서버 hello_ack가 JSON 객체가 아닙니다.")
        try:
            return HelloAckMessage.from_mapping(payload)
        except (TypeError, ValueError) as exc:
            raise ConnectionError(f"서버 hello_ack 검증 실패: {exc}") from exc

    async def _run_connected_session(self, websocket) -> None:
        await self._perform_handshake(websocket)
        self.controller.set_remote_connected(True)
        print(f"VPS 원격 서버 연결 완료: {self.url}")
        tasks = {
            asyncio.create_task(self._receive_loop(websocket)),
            asyncio.create_task(self._send_loop(websocket)),
            asyncio.create_task(self._telemetry_loop()),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.result()

    async def _receive_loop(self, websocket) -> None:
        async for raw in websocket:
            payload = json.loads(raw)
            if payload.get("type") != "command":
                continue
            await asyncio.to_thread(self.controller.handle_remote_message, payload)

    async def _send_loop(self, websocket) -> None:
        if self._buffer is None:
            raise RuntimeError("원격 전송 버퍼가 준비되지 않았습니다.")
        while not self._stop.is_set():
            outgoing, event = await self._buffer.get()
            try:
                if event.get("type") == "camera" and event.get("image_bytes"):
                    metadata = dict(event)
                    image = metadata.pop("image_bytes")
                    payload = pack_binary_event(metadata, image)
                else:
                    payload = json.dumps(event, ensure_ascii=False)
                try:
                    await asyncio.wait_for(
                        websocket.send(payload),
                        timeout=self.send_timeout,
                    )
                except asyncio.TimeoutError as exc:
                    raise ConnectionError(
                        f"WebSocket 송신이 {self.send_timeout:.1f}초 동안 완료되지 않았습니다."
                    ) from exc
            finally:
                outgoing.task_done()

    async def _next_outgoing_event(self) -> tuple[asyncio.Queue, dict[str, Any]]:
        if self._buffer is None:
            raise RuntimeError("원격 전송 버퍼가 준비되지 않았습니다.")
        return await self._buffer.get()

    async def _telemetry_loop(self) -> None:
        while not self._stop.is_set():
            telemetry = await asyncio.to_thread(self.controller.telemetry_snapshot)
            self.publish(telemetry)
            await asyncio.sleep(self.telemetry_interval)
