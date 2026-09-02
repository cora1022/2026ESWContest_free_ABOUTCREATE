"""Domain types shared by the robot application layers."""

from robot_app.domain.commands import RobotCommand
from robot_app.domain.state import RobotState

__all__ = ["RobotCommand", "RobotState"]
