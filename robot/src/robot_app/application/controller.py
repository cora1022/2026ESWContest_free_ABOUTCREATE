from __future__ import annotations

import base64
import queue
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from robot_app.config import RobotSettings
from robot_app.domain.commands import DIRECTIONS, RobotCommand
from robot_app.domain.ports import ActionsPort, EventListener, GnssPort, HardwarePort
from robot_app.domain.state import RobotState


class RobotController:
    """Serialize local actions and guard lease-based remote driving."""

    def __init__(
        self,
        hardware: HardwarePort,
        actions: ActionsPort,
        gnss: GnssPort | None = None,
        settings: RobotSettings | None = None,
    ) -> None:
        self.hw = hardware
        self.actions = actions
        self.gnss = gnss
        self.settings = settings or RobotSettings.from_env()
        remote = self.settings.remote
        self.robot_id = remote.robot_id
        self.safe_distance_cm = self.settings.ultrasonic.safe_distance_cm
        self.default_lease_ms = remote.drive_lease_ms
        self.video_fps = remote.video_fps
        self.video_lease_ms = remote.video_lease_ms
        self.video_jpeg_quality = remote.video_jpeg_quality

        self._state = RobotState(updated_at=time.time())
        self._state_lock = threading.RLock()
        self._jobs: queue.Queue[tuple[str, RobotCommand]] = queue.Queue(maxsize=20)
        self._running = threading.Event()
        self._worker: threading.Thread | None = None
        self._watchdog: threading.Thread | None = None
        self._remote_deadline = 0.0
        self._video_deadline = 0.0
        self._video_stop = threading.Event()
        self._video_thread: threading.Thread | None = None
        self._busy_action = False
        self._listener: EventListener | None = None
        if hasattr(self.hw, "set_speech_listener"):
            self.hw.set_speech_listener(self._publish_speech)

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._worker = threading.Thread(target=self._worker_loop, name="robot-actions", daemon=True)
        self._watchdog = threading.Thread(target=self._watchdog_loop, name="remote-watchdog", daemon=True)
        self._worker.start()
        self._watchdog.start()

    def shutdown(self) -> None:
        self._running.clear()
        self.stop_video_stream("controller_shutdown", emit_status=False)
        self.emergency_stop("controller_shutdown")
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2.0)
        if self._watchdog and self._watchdog.is_alive():
            self._watchdog.join(timeout=2.0)
        if hasattr(self.hw, "set_speech_listener"):
            self.hw.set_speech_listener(None)

    def set_event_listener(self, listener: EventListener | None) -> None:
        self._listener = listener

    def set_remote_connected(self, connected: bool) -> None:
        with self._state_lock:
            self._state.remote_connected = connected
            self._state.updated_at = time.time()
        if not connected:
            self.remote_disconnected()

    def remote_disconnected(self) -> None:
        with self._state_lock:
            was_remote = self._state.remote_control_active
        if was_remote:
            self.emergency_stop("remote_disconnected")
        self.stop_video_stream("remote_disconnected")
        self._emit({"type": "status", "event": "remote_disconnected"})

    def submit_local_text(self, text: str) -> bool:
        value = str(text or "").strip()
        if not value:
            return False
        with self._state_lock:
            if self._state.remote_control_active:
                return False
        command = RobotCommand(
            command_id=f"local-{time.time_ns()}",
            action="TEXT_COMMAND",
            text=value,
        )
        return self._enqueue("local", command)

    def execute_local_text(self, text: str) -> bool:
        """Run local voice actions while keeping remote STOP available."""
        value = str(text or "").strip()
        if not value:
            return False
        with self._state_lock:
            if self._state.remote_control_active or self._busy_action:
                return False
            self._busy_action = True
            self._state.mode = "LOCAL"
            self._state.last_command_id = f"local-{time.time_ns()}"
            self._state.last_command = "TEXT_COMMAND"
            self._state.updated_at = time.time()
        try:
            if hasattr(self.actions, "reset_cancel"):
                self.actions.reset_cancel()
            self.actions.handle_command(value)
            return True
        finally:
            self._busy_action = False
            with self._state_lock:
                self._state.motion = "STOPPED"
                self._state.updated_at = time.time()

    def handle_remote_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            command = RobotCommand.from_message(payload)
        except ValueError as exc:
            result = self._result(str(payload.get("id") or ""), "rejected", str(exc))
            self._emit(result)
            return result
        if command.is_expired():
            result = self._result(command.command_id, "rejected", "expired")
            self._emit(result)
            return result
        if command.action == "STOP":
            self.emergency_stop("remote_stop", command.command_id)
            result = self._result(command.command_id, "completed", "stopped")
            self._emit(result)
            return result
        if command.action == "VIDEO_START":
            return self._refresh_video_stream(command)
        if command.action == "VIDEO_STOP":
            self.stop_video_stream("remote_video_stop", emit_status=False)
            result = self._result(command.command_id, "completed", "video_stopped")
            self._emit(result)
            return result
        if command.action in DIRECTIONS:
            return self._refresh_remote_drive(command)
        if self._enqueue("remote", command):
            result = self._result(command.command_id, "accepted", "queued")
        else:
            result = self._result(command.command_id, "rejected", "queue_full")
        self._emit(result)
        return result

    def emergency_stop(self, reason: str, command_id: str = "") -> None:
        if hasattr(self.actions, "cancel_current"):
            self.actions.cancel_current()
        self.hw.stop_motors()
        with self._jobs.mutex:
            self._jobs.queue.clear()
        with self._state_lock:
            self._remote_deadline = 0.0
            self._state.mode = "LOCAL"
            self._state.motion = "STOPPED"
            self._state.remote_control_active = False
            self._state.last_command_id = command_id or self._state.last_command_id
            self._state.last_command = "STOP"
            self._state.last_result = reason
            self._state.updated_at = time.time()
        self._emit({"type": "status", "event": "stopped", "reason": reason})

    def _publish_speech(
        self,
        text: str,
        audio_bytes: bytes | None = None,
        audio_content_type: str = "audio/mpeg",
    ) -> None:
        caption = str(text or "").strip()
        if not caption:
            return
        event: dict[str, Any] = {
            "type": "speech",
            "robot_id": self.robot_id,
            "text": caption[:500],
            "timestamp": time.time(),
        }
        if audio_bytes and len(audio_bytes) <= 2_000_000:
            event["audio_b64"] = base64.b64encode(audio_bytes).decode("ascii")
            event["audio_content_type"] = audio_content_type
        self._emit(event)

    def _refresh_video_stream(self, command: RobotCommand) -> dict[str, Any]:
        lease_ms = max(3_000, min(command.duration_ms or self.video_lease_ms, 10_000))
        with self._state_lock:
            already_active = bool(self._video_thread and self._video_thread.is_alive())
            self._video_deadline = time.monotonic() + lease_ms / 1000.0
            self._state.video_active = True
            self._state.updated_at = time.time()
        if not already_active:
            self._video_stop.clear()
            self._video_thread = threading.Thread(
                target=self._video_loop,
                name="remote-video",
                daemon=True,
            )
            self._video_thread.start()
        reason = "video_lease_refreshed" if already_active else "video_started"
        result = self._result(command.command_id, "accepted", reason)
        self._emit(result)
        return result

    def stop_video_stream(self, reason: str = "video_stopped", emit_status: bool = True) -> None:
        with self._state_lock:
            was_active = self._state.video_active
            self._video_deadline = 0.0
            self._state.video_active = False
            self._state.updated_at = time.time()
        self._video_stop.set()
        thread = self._video_thread
        if thread and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=1.5)
        if thread and not thread.is_alive():
            self._video_thread = None
        if was_active and emit_status:
            self._emit(
                {
                    "type": "status",
                    "event": "video_stopped",
                    "reason": reason,
                    "timestamp": time.time(),
                }
            )

    def _video_loop(self) -> None:
        frame_interval = 1.0 / self.video_fps
        try:
            while self._running.is_set() and not self._video_stop.is_set():
                started_at = time.monotonic()
                image = self._capture_jpeg_bytes(self.video_jpeg_quality)
                if len(image) > 2_000_000:
                    raise ValueError("카메라 이미지가 2MB를 초과했습니다.")
                self._emit(
                    {
                        "type": "camera",
                        "robot_id": self.robot_id,
                        "content_type": "image/jpeg",
                        "image_bytes": image,
                        "stream": True,
                        "timestamp": time.time(),
                    }
                )
                elapsed = time.monotonic() - started_at
                self._video_stop.wait(max(0.0, frame_interval - elapsed))
        except Exception as exc:
            with self._state_lock:
                self._state.last_error = f"video: {exc}"
            self._emit(
                {
                    "type": "status",
                    "event": "video_failed",
                    "reason": str(exc),
                    "timestamp": time.time(),
                }
            )
        finally:
            with self._state_lock:
                self._state.video_active = False
                self._state.updated_at = time.time()
            self._video_thread = None

    def telemetry_snapshot(self, sample_distance: bool = True) -> dict[str, Any]:
        if sample_distance and not self._busy_action:
            try:
                distance = float(self.hw.get_distance_cm())
                with self._state_lock:
                    self._state.distance_cm = round(distance, 1)
                    self._state.obstacle = distance <= self.safe_distance_cm
                    self._state.updated_at = time.time()
            except Exception as exc:
                with self._state_lock:
                    self._state.last_error = f"distance: {exc}"
                    self._state.obstacle = True
                    self._state.updated_at = time.time()
        with self._state_lock:
            state = asdict(self._state)
        state.update({"type": "telemetry", "robot_id": self.robot_id, "timestamp": time.time()})
        if hasattr(self.hw, "health_snapshot"):
            state["hardware_health"] = self.hw.health_snapshot()
        if self.gnss:
            state["location"] = self.gnss.snapshot()
        return state

    def _refresh_remote_drive(self, command: RobotCommand) -> dict[str, Any]:
        with self._state_lock:
            if self._busy_action:
                result = self._result(command.command_id, "rejected", "local_action_busy")
                self._emit(result)
                return result
        distance = None
        if command.action == "FORWARD":
            try:
                distance = float(self.hw.get_distance_cm())
            except Exception as exc:
                self.emergency_stop("distance_sensor_error", command.command_id)
                result = self._result(
                    command.command_id,
                    "rejected",
                    f"distance_sensor_error: {exc}",
                )
                self._emit(result)
                return result
            if distance <= self.safe_distance_cm:
                self.emergency_stop("obstacle_detected", command.command_id)
                with self._state_lock:
                    self._state.distance_cm = round(distance, 1)
                    self._state.obstacle = True
                result = self._result(
                    command.command_id,
                    "rejected",
                    "obstacle_detected",
                    distance_cm=distance,
                )
                self._emit(result)
                return result
        if hasattr(self.actions, "cancel_current"):
            self.actions.cancel_current()
        self.hw.start_continuous_motion(command.action)
        lease_ms = max(250, min(command.duration_ms or self.default_lease_ms, 1_000))
        with self._state_lock:
            self._remote_deadline = time.monotonic() + lease_ms / 1000.0
            self._state.mode = "REMOTE"
            self._state.motion = command.action
            self._state.remote_control_active = True
            self._state.obstacle = False
            self._state.distance_cm = (
                round(distance, 1) if distance is not None else self._state.distance_cm
            )
            self._state.last_command_id = command.command_id
            self._state.last_command = command.action
            self._state.last_result = "driving"
            self._state.updated_at = time.time()
        result = self._result(command.command_id, "accepted", "lease_refreshed")
        self._emit(result)
        return result

    def _enqueue(self, source: str, command: RobotCommand) -> bool:
        try:
            self._jobs.put_nowait((source, command))
            return True
        except queue.Full:
            return False

    def _worker_loop(self) -> None:
        while self._running.is_set():
            try:
                source, command = self._jobs.get(timeout=0.2)
            except queue.Empty:
                continue
            self._busy_action = True
            with self._state_lock:
                self._state.mode = "REMOTE_ACTION" if source == "remote" else "LOCAL"
                self._state.last_command_id = command.command_id
                self._state.last_command = command.action
                self._state.updated_at = time.time()
            try:
                if hasattr(self.actions, "reset_cancel"):
                    self.actions.reset_cancel()
                if command.action == "TEXT_COMMAND":
                    if not command.text:
                        raise ValueError("text가 비어 있습니다.")
                    self.actions.handle_command(command.text)
                    self._emit(
                        self._result(
                            command.command_id,
                            "completed",
                            "text_command_finished",
                        )
                    )
                elif command.action == "GET_DISTANCE":
                    distance = float(self.hw.get_distance_cm())
                    self._emit(
                        self._result(
                            command.command_id,
                            "completed",
                            "distance",
                            distance_cm=distance,
                        )
                    )
                elif command.action == "CAPTURE_IMAGE":
                    self._capture_and_emit(command.command_id)
            except Exception as exc:
                self.hw.stop_motors()
                with self._state_lock:
                    self._state.last_error = str(exc)
                self._emit(self._result(command.command_id, "failed", str(exc)))
            finally:
                self._busy_action = False
                with self._state_lock:
                    if not self._state.remote_control_active:
                        self._state.mode = "LOCAL"
                        self._state.motion = "STOPPED"
                    self._state.updated_at = time.time()
                self._jobs.task_done()

    def _capture_and_emit(self, command_id: str) -> None:
        image = self._capture_jpeg_bytes()
        if len(image) > 2_000_000:
            raise ValueError("카메라 이미지가 2MB를 초과했습니다.")
        self._emit(
            {
                "type": "camera",
                "command_id": command_id,
                "content_type": "image/jpeg",
                "image_bytes": image,
                "stream": False,
                "timestamp": time.time(),
            }
        )
        self._emit(self._result(command_id, "completed", "camera_captured"))

    def _capture_jpeg_bytes(self, quality: int | None = None) -> bytes:
        if hasattr(self.hw, "capture_jpeg"):
            return bytes(self.hw.capture_jpeg(quality=quality))
        image_path = self.hw.capture_image()
        path = Path(image_path)
        try:
            return path.read_bytes()
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def _watchdog_loop(self) -> None:
        while self._running.is_set():
            with self._state_lock:
                drive_expired = (
                    self._state.remote_control_active
                    and time.monotonic() >= self._remote_deadline
                )
                video_expired = (
                    self._state.video_active
                    and time.monotonic() >= self._video_deadline
                )
            if drive_expired:
                self.emergency_stop("remote_lease_expired")
            if video_expired:
                self.stop_video_stream("video_lease_expired")
            time.sleep(0.03)

    def _result(
        self,
        command_id: str,
        status: str,
        reason: str,
        **extra: Any,
    ) -> dict[str, Any]:
        result = {
            "type": "command_result",
            "robot_id": self.robot_id,
            "command_id": command_id,
            "status": status,
            "reason": reason,
            "timestamp": time.time(),
        }
        result.update(extra)
        with self._state_lock:
            self._state.last_command_id = command_id or self._state.last_command_id
            self._state.last_result = f"{status}: {reason}"
            self._state.updated_at = time.time()
        return result

    def _emit(self, event: dict[str, Any]) -> None:
        listener = self._listener
        if listener:
            try:
                listener(event)
            except Exception as exc:
                print(f"원격 이벤트 전달 실패: {exc}")
