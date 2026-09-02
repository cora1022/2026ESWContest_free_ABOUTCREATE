from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from server.dependencies import get_hub, request_session
from server.schemas import ALLOWED_ACTIONS, CommandRequest, build_command, normalize_action
from server.services.robot_hub import RobotHub


router = APIRouter(prefix="/api", tags=["control"])


@router.get("/status")
async def status(
    _: str = Depends(request_session),
    hub: RobotHub = Depends(get_hub),
) -> dict[str, Any]:
    return {
        "state": hub.state,
        "events": hub.event_log.latest(),
        "camera_time": hub.camera_time,
    }


@router.get("/locations")
async def locations(
    _: str = Depends(request_session),
    hub: RobotHub = Depends(get_hub),
) -> dict[str, Any]:
    return {"locations": list(hub.locations)}


@router.get("/camera/latest")
async def latest_camera(
    _: str = Depends(request_session),
    hub: RobotHub = Depends(get_hub),
) -> Response:
    if hub.camera_image is None:
        raise HTTPException(status_code=404, detail="아직 촬영된 이미지가 없습니다.")
    return Response(content=hub.camera_image, media_type="image/jpeg")


async def _issue_command(body: CommandRequest, hub: RobotHub) -> dict[str, Any]:
    action = normalize_action(body.action)
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=422, detail="허용되지 않은 명령입니다.")
    if action == "TEXT_COMMAND" and not body.text.strip():
        raise HTTPException(status_code=422, detail="자연어 명령이 비어 있습니다.")

    command = build_command(body)
    await hub.send_command(command)
    if action != "VIDEO_START" or not hub.state.get("video_active"):
        await hub.record({"type": "command_sent", "command_id": command["id"], "action": action})
    return {"accepted": True, "command_id": command["id"]}


@router.post("/camera")
async def request_camera(
    _: str = Depends(request_session),
    hub: RobotHub = Depends(get_hub),
) -> dict[str, Any]:
    return await _issue_command(CommandRequest(action="CAPTURE_IMAGE"), hub)


@router.post("/command")
async def issue_command(
    body: CommandRequest,
    _: str = Depends(request_session),
    hub: RobotHub = Depends(get_hub),
) -> dict[str, Any]:
    return await _issue_command(body, hub)
