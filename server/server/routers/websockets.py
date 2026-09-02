from __future__ import annotations

import asyncio
import json
import secrets
import time
from contextlib import suppress

from anyio import CancelScope
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from robot_protocol.messages import HelloMessage
from robot_protocol.transport import unpack_binary_event
from robot_protocol.version import PROTOCOL_VERSION
from server.services.container import AppServices
from server.services.robot_messages import consume_robot_message


router = APIRouter(tags=["realtime"])


def _services(websocket: WebSocket) -> AppServices:
    return websocket.app.state.services


@router.websocket("/ws/robot")
async def robot_websocket(websocket: WebSocket) -> None:
    services = _services(websocket)
    settings = services.settings
    hub = services.hub
    disconnect_reason = "robot connection closed"
    disconnect_code: int | None = None
    await websocket.accept()
    try:
        hello = await asyncio.wait_for(websocket.receive_json(), timeout=8.0)
        try:
            robot_hello = HelloMessage.from_mapping(hello)
        except ValueError:
            await websocket.close(code=1008, reason="invalid robot identity")
            return
        if robot_hello.robot_id != settings.robot_id:
            await websocket.close(code=1008, reason="invalid robot identity")
            return
        if not secrets.compare_digest(robot_hello.token, settings.robot_token):
            await websocket.close(code=1008, reason="invalid robot token")
            return

        await hub.replace_robot(websocket)
        await websocket.send_json(
            {
                "type": "hello_ack",
                "server_time": time.time(),
                "protocol_version": PROTOCOL_VERSION,
            }
        )
        await hub.record({"type": "robot_connected", "robot_id": settings.robot_id})
        await hub.broadcast({"type": "state", "state": hub.state})

        while True:
            packet = await websocket.receive()
            if packet.get("type") == "websocket.disconnect":
                break
            if packet.get("bytes") is not None:
                message, binary_payload = unpack_binary_event(packet["bytes"])
                message["binary_payload"] = binary_payload
            else:
                message = json.loads(packet.get("text") or "{}")
            await consume_robot_message(hub, message)
    except WebSocketDisconnect:
        disconnect_reason = "robot connection closed"
    except asyncio.TimeoutError:
        disconnect_reason = "robot hello timeout"
        disconnect_code = 1008
    except Exception as exc:
        disconnect_reason = "robot protocol error"
        disconnect_code = 1011
        print(f"로봇 WebSocket 오류: {exc}")
    finally:
        with CancelScope(shield=True):
            disconnected = await hub.disconnect_robot(
                websocket,
                close_socket=disconnect_code is not None,
                code=disconnect_code or 1000,
                reason=disconnect_reason,
            )
            if not disconnected and disconnect_code is not None:
                with suppress(Exception):
                    await websocket.close(code=disconnect_code, reason=disconnect_reason)


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket, session: str = Query(default="")) -> None:
    services = _services(websocket)
    token = websocket.cookies.get(services.settings.session_cookie_name, "") or session
    if not services.sessions.valid(token):
        await websocket.close(code=1008, reason="invalid dashboard session")
        return
    await websocket.accept()
    peer = services.hub.add_dashboard(websocket, token)
    peer.offer_event({"type": "state", "state": services.hub.state})

    async def monitor_session() -> None:
        while not peer.closed.is_set():
            try:
                await asyncio.wait_for(peer.closed.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                if not services.sessions.valid(token):
                    await services.hub.remove_dashboard(
                        websocket,
                        close_socket=True,
                        code=1008,
                        reason="dashboard session expired",
                    )
                    return

    session_monitor = asyncio.create_task(monitor_session(), name="dashboard-session-monitor")
    try:
        while not peer.closed.is_set():
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with CancelScope(shield=True):
            session_monitor.cancel()
            await asyncio.gather(session_monitor, return_exceptions=True)
            await services.hub.remove_dashboard(websocket, close_socket=False)
