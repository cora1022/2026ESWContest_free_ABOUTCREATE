from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv

from robot_app.config import RobotSettings


@dataclass
class RobotRuntime:
    hardware: object
    actions: object
    controller: object
    gnss: object
    remote: object

    def start(self) -> None:
        self.controller.start()
        self.gnss.start()
        self.remote.start()

    def stop(self) -> None:
        self.remote.stop()
        self.controller.shutdown()
        self.gnss.stop()
        self.hardware.cleanup()


def build_runtime(settings: RobotSettings | None = None) -> RobotRuntime:
    load_dotenv()
    resolved = settings or RobotSettings.from_env()

    from robot_app.actions.service import RobotActions
    from robot_app.application.controller import RobotController
    from robot_app.hardware.facade import RobotHardware
    from robot_app.infrastructure.gnss import GnssReader
    from robot_app.infrastructure.remote_client import RobotRemoteClient

    hardware = RobotHardware(resolved)
    actions = RobotActions(hardware, resolved)
    gnss = GnssReader(resolved.gnss)
    controller = RobotController(hardware, actions, gnss=gnss, settings=resolved)
    remote = RobotRemoteClient(controller, resolved.remote)
    return RobotRuntime(hardware, actions, controller, gnss, remote)


def main() -> None:
    from robot_app.application.voice import run_voice_loop

    runtime = build_runtime()
    runtime.start()
    try:
        run_voice_loop(runtime.hardware, runtime.controller)
    except KeyboardInterrupt:
        print("\n사용자가 종료했습니다.")
    finally:
        runtime.stop()
