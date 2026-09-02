import time
from typing import Any

from fastapi import APIRouter, Depends

from server.dependencies import get_hub
from server.services.robot_hub import RobotHub


router = APIRouter()


@router.get("/health")
async def health(hub: RobotHub = Depends(get_hub)) -> dict[str, Any]:
    return {"status": "ok", "robot_online": bool(hub.robot), "server_time": time.time()}
