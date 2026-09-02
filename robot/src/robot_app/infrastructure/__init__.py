"""External system adapters for networking and GNSS."""

from robot_app.infrastructure.gnss import GnssReader
from robot_app.infrastructure.remote_client import RobotRemoteClient

__all__ = ["GnssReader", "RobotRemoteClient"]
