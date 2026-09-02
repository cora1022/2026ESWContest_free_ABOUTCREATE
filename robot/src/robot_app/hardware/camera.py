from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path

from robot_app.config import CameraSettings


class UsbCamera:
    def __init__(self, settings: CameraSettings, initialize: bool = True) -> None:
        self.settings = settings
        self.capture = None
        self._lock = threading.Lock()
        if initialize:
            self.setup()

    def setup(self) -> None:
        if self.capture is not None:
            return
        try:
            import cv2

            capture = cv2.VideoCapture(self.settings.index, cv2.CAP_V4L2)
            if not capture.isOpened():
                capture.release()
                capture = cv2.VideoCapture(self.settings.index)
            if not capture.isOpened():
                print(f"⚠️ USB 카메라를 열 수 없습니다. CAMERA_INDEX={self.settings.index}")
                return
            if len(self.settings.input_format) == 4:
                capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.settings.input_format))
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
            capture.set(cv2.CAP_PROP_FPS, self.settings.input_fps)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if hasattr(cv2, "CAP_PROP_AUTOFOCUS"):
                capture.set(cv2.CAP_PROP_AUTOFOCUS, 1 if self.settings.autofocus else 0)

            for _ in range(self.settings.warmup_frames):
                ready, _ = capture.read()
                if not ready:
                    break
                time.sleep(1.0 / self.settings.input_fps)

            self.capture = capture
            actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = capture.get(cv2.CAP_PROP_FPS)
            fourcc_value = int(capture.get(cv2.CAP_PROP_FOURCC))
            fourcc = "".join(chr((fourcc_value >> (8 * index)) & 0xFF) for index in range(4)).strip()
            print(
                "✅ USB 카메라 준비 완료: "
                f"index={self.settings.index}, {actual_width}x{actual_height}, "
                f"format={fourcc or self.settings.input_format}, fps={actual_fps:.1f}, "
                f"autofocus={'on' if self.settings.autofocus else 'off'}"
            )
        except Exception as exc:
            self.capture = None
            print(f"⚠️ 카메라 초기화 실패: {exc}")

    def capture_jpeg(self, quality: int | None = None) -> bytes:
        if self.capture is None:
            raise RuntimeError("카메라가 준비되지 않았습니다.")
        import cv2

        frame = None
        ready = False
        with self._lock:
            for _ in range(self.settings.flush_frames + 1):
                ready, frame = self.capture.read()
        if not ready or frame is None:
            raise RuntimeError("USB 카메라에서 프레임을 읽지 못했습니다.")

        jpeg_quality = max(30, min(int(quality or self.settings.jpeg_quality), 95))
        encoded_ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if not encoded_ok:
            raise RuntimeError("카메라 프레임을 JPEG로 변환하지 못했습니다.")
        return encoded.tobytes()

    def capture_image(self, path: str | None = None) -> str:
        target = Path(path or f"/tmp/robot_camera_{uuid.uuid4().hex}.jpg")
        target.write_bytes(self.capture_jpeg())
        print(f"📷 즉시 캡처 완료: {target}")
        return str(target)

    def close(self) -> None:
        if self.capture is None:
            return
        try:
            self.capture.release()
            print("📷 카메라 종료")
        finally:
            self.capture = None
