"""Compatibility import for the application controller."""

from robot_app.application.controller import RobotController
from robot_app.domain.state import RobotState

__all__ = ["RobotController", "RobotState"]
