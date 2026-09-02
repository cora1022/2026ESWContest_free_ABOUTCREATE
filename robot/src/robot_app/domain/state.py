from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RobotState:
    mode: str = "LOCAL"
    motion: str = "STOPPED"
    remote_connected: bool = False
    remote_control_active: bool = False
    video_active: bool = False
    obstacle: bool = False
    distance_cm: float | None = None
    last_command_id: str = ""
    last_command: str = ""
    last_result: str = ""
    last_error: str = ""
    updated_at: float = 0.0
