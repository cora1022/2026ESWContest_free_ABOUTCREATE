"""
hardware.py
라즈베리파이 로봇 실제 장치 제어 계층
- 모터: RC_CAR.py에서 성공한 BCM 핀 5,6,16,26 사용
- 초음파: HC-SR04 TRIG=GPIO23, ECHO=GPIO24
- LED: GPIO25
  * 명령 시작 대기 중: OFF
  * 실제 명령 듣는 중: ON
  * Gemini/카메라/동작 처리 중: BLINK
- 마이크: arecord raw stream + SpeechRecognition
- 카메라: OpenCV USB 카메라
- TTS/음악: pygame 대신 mpg123/ffplay 외부 플레이어 사용
"""
import os
import time
import wave
import audioop
import subprocess
import uuid
import shutil
import hashlib
import threading
import re
from pathlib import Path
from collections import deque

# -----------------------------
# GPIO pins
# -----------------------------
IN1 = 5
IN2 = 6
IN3 = 16
IN4 = 26

ULTRASONIC_TRIG = int(os.getenv("ULTRASONIC_TRIG", "23"))
ULTRASONIC_ECHO = int(os.getenv("ULTRASONIC_ECHO", "24"))
COMMAND_LED_PIN = int(os.getenv("COMMAND_LED_PIN", "25"))

# -----------------------------
# Audio settings
# -----------------------------
AUDIO_DEVICE = os.getenv("AUDIO_DEVICE", "plughw:3,0")
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
AUDIO_CHANNELS = 1
AUDIO_WIDTH_BYTES = 2
AUDIO_CHUNK_MS = int(os.getenv("AUDIO_CHUNK_MS", "80"))
AUDIO_MIN_ENERGY = int(os.getenv("AUDIO_MIN_ENERGY", "430"))
AUDIO_NOISE_MULTIPLIER = float(os.getenv("AUDIO_NOISE_MULTIPLIER", "2.0"))
AUDIO_DEBUG = os.getenv("AUDIO_DEBUG", "0") == "1"
USE_TTS = os.getenv("USE_TTS", "1") == "1"
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "0.9"))
TTS_TIMEOUT_SEC = os.getenv("TTS_TIMEOUT_SEC", "")  # 비워두면 TTS를 끝까지 재생합니다.
TTS_CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", "/tmp/robot_tts_cache"))

# -----------------------------
# Camera settings
# -----------------------------
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "1"))
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "480"))
CAMERA_JPEG_QUALITY = int(os.getenv("CAMERA_JPEG_QUALITY", "75"))

# -----------------------------
# Ultrasonic settings
# -----------------------------
ULTRASONIC_ENABLED = os.getenv("ULTRASONIC_ENABLED", "1") == "1"
SAFE_DISTANCE_CM = float(os.getenv("SAFE_DISTANCE_CM", "25"))
ULTRASONIC_STOP_CM = float(os.getenv("ULTRASONIC_STOP_CM", "18"))
SENSOR_FAIL_DISTANCE_CM = 0.0

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    GPIO_AVAILABLE = False


def clean_tts_text(text):
    """TTS에 넣기 전 마크다운/따옴표/행동 지시문을 제거합니다."""
    text = str(text or "").strip()
    if not text:
        return ""

    # 코드블록, 인라인 코드, 마크다운 기호 제거
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)

    # 사용자가 요청한 기호 제거: *, 큰따옴표.
    # 그 외 TTS가 어색하게 읽는 따옴표류도 함께 제거합니다.
    for ch in ['*', '"', "'", "“", "”", "‘", "’", "「", "」", "『", "』"]:
        text = text.replace(ch, "")

    # 괄호 안에 있는 파일 재생/행동 설명은 대사가 아니라서 제거
    text = re.sub(r"\([^)]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[[^\]]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^\]]*\]", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return text


class RobotHardware:
    def __init__(self):
        self.gpio_ready = False
        self.camera = None
        self._blink_thread = None
        self._blink_stop = threading.Event()
        self.setup_gpio()
        self.setup_camera()

    # -----------------------------
    # GPIO / LED
    # -----------------------------
    def setup_gpio(self):
        if not GPIO_AVAILABLE:
            print("⚠️ RPi.GPIO를 불러오지 못했습니다. 테스트 모드로 동작합니다.")
            return

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in [IN1, IN2, IN3, IN4, ULTRASONIC_TRIG, COMMAND_LED_PIN]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)
        self.gpio_ready = True
        print("✅ 실제 GPIO 하드웨어 모드 활성화")
        print(f"💡 LED: GPIO{COMMAND_LED_PIN}")

    def _set_led(self, value: bool):
        if self.gpio_ready:
            GPIO.output(COMMAND_LED_PIN, GPIO.HIGH if value else GPIO.LOW)

    def command_led_on(self):
        self.stop_led_blink(force_message=False)
        self._set_led(True)
        print("💡 LED ON")

    def command_led_off(self):
        self.stop_led_blink(force_message=False)
        self._set_led(False)
        print("💡 LED OFF")

    def start_led_blink(self, interval=0.25):
        if self._blink_thread and self._blink_thread.is_alive():
            return
        self._blink_stop.clear()

        def _blink_loop():
            state = False
            while not self._blink_stop.is_set():
                state = not state
                self._set_led(state)
                time.sleep(interval)
            self._set_led(False)

        self._blink_thread = threading.Thread(target=_blink_loop, daemon=True)
        self._blink_thread.start()
        print("💡 LED BLINK START")

    def stop_led_blink(self, force_message=True):
        if self._blink_thread and self._blink_thread.is_alive():
            self._blink_stop.set()
            self._blink_thread.join(timeout=1.0)
            self._blink_thread = None
            if force_message:
                print("💡 LED BLINK STOP")
        self._set_led(False)

    # -----------------------------
    # Motor
    # -----------------------------
    def _write_motors(self, in1, in2, in3, in4):
        if not self.gpio_ready:
            print(f"[TEST MOTOR] IN1={in1}, IN2={in2}, IN3={in3}, IN4={in4}")
            return
        GPIO.output(IN1, GPIO.HIGH if in1 else GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH if in2 else GPIO.LOW)
        GPIO.output(IN3, GPIO.HIGH if in3 else GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH if in4 else GPIO.LOW)

    def stop_motors(self):
        self._write_motors(0, 0, 0, 0)
        print("🛑 모터 정지")

    def move_forward(self, seconds=0.45):
        distance = self.get_distance_cm()
        if distance <= SAFE_DISTANCE_CM:
            self.stop_motors()
            print(f"🚧 전방 {distance:.1f}cm 장애물 감지. 전진 취소.")
            return False
        print(f"⬆️ 전진 {seconds:.2f}초")
        self._write_motors(1, 0, 1, 0)
        time.sleep(seconds)
        self.stop_motors()
        return True

    def move_backward(self, seconds=0.6):
        print(f"⬇️ 후진 {seconds:.2f}초")
        self._write_motors(0, 1, 0, 1)
        time.sleep(seconds)
        self.stop_motors()
        return True

    def turn_left(self, seconds=4.0):
        print(f"↩️ 좌회전 {seconds:.2f}초")
        self._write_motors(0, 1, 1, 0)
        time.sleep(seconds)
        self.stop_motors()
        return True

    def turn_right(self, seconds=4.0):
        print(f"↪️ 우회전 {seconds:.2f}초")
        self._write_motors(1, 0, 0, 1)
        time.sleep(seconds)
        self.stop_motors()
        return True

    def turn_around(self, seconds=8.0):
        print(f"🔄 뒤로 돌기 {seconds:.2f}초")
        return self.turn_right(seconds)

    def move_forward_until_obstacle(self, stop_cm=None, max_seconds=12.0):
        stop_cm = float(stop_cm or ULTRASONIC_STOP_CM)
        print(f"⬆️ 초음파 전용 전진 시작: 정지거리={stop_cm:.1f}cm")
        start = time.monotonic()
        last_distance = None

        while time.monotonic() - start < max_seconds:
            distance = self.get_distance_cm()
            last_distance = distance
            if distance <= stop_cm:
                self.stop_motors()
                return last_distance
            self._write_motors(1, 0, 1, 0)
            time.sleep(0.22)
            self.stop_motors()
            time.sleep(0.06)

        self.stop_motors()
        return last_distance

    # -----------------------------
    # Ultrasonic
    # -----------------------------
    def get_distance_cm(self):
        if not ULTRASONIC_ENABLED:
            print("📏 [센서 비활성화] 테스트용 거리: 100cm")
            return 100.0
        if not self.gpio_ready:
            print("📏 [가상 센서] 전방 거리: 100cm")
            return 100.0

        readings = []
        timeout_count = 0
        stuck_high_count = 0

        for _ in range(3):
            distance, status = self._get_distance_once()
            if status == "ok":
                readings.append(distance)
            elif status == "timeout":
                timeout_count += 1
            elif status == "stuck_high":
                stuck_high_count += 1
            time.sleep(0.04)

        if readings:
            readings.sort()
            distance_cm = readings[len(readings) // 2]
            print(f"📏 전방 거리: {distance_cm:.1f}cm")
            return float(distance_cm)

        # ECHO가 HIGH로 고정된 상태는 배선/센서 이상 가능성이 커서 안전상 정지 처리
        if stuck_high_count > 0:
            print("⚠️ 초음파 ECHO가 처음부터 HIGH입니다. 안전상 0cm 처리.")
            return SENSOR_FAIL_DISTANCE_CM

        # 반사파가 안 돌아온 경우는 너무 멀거나 앞이 비어 있는 상황일 수 있음
        if timeout_count > 0:
            max_distance = float(os.getenv("ULTRASONIC_MAX_CM", "400"))
            print(f"📏 초음파 반사 없음. 앞이 멀다고 보고 {max_distance:.0f}cm 처리.")
            return max_distance

        print("⚠️ 초음파 측정 실패. 안전상 0cm 처리.")
        return SENSOR_FAIL_DISTANCE_CM

    def _get_distance_once(self):
        try:
            if GPIO.input(ULTRASONIC_ECHO) == 1:
                time.sleep(0.002)
                if GPIO.input(ULTRASONIC_ECHO) == 1:
                    return None, "stuck_high"

            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)
            time.sleep(0.0002)
            GPIO.output(ULTRASONIC_TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)

            timeout = time.monotonic() + 0.03
            while GPIO.input(ULTRASONIC_ECHO) == 0:
                if time.monotonic() > timeout:
                    return None, "timeout"
            start = time.monotonic()

            timeout = start + 0.03
            while GPIO.input(ULTRASONIC_ECHO) == 1:
                if time.monotonic() > timeout:
                    return None, "timeout"
            end = time.monotonic()

            distance_cm = (end - start) * 34300 / 2
            if distance_cm < 2 or distance_cm > 400:
                return None, "timeout"
            return float(distance_cm), "ok"

        except Exception as e:
            print(f"⚠️ 거리 측정 실패: {e}")
            return None, "fail"

    # -----------------------------
    # Camera
    # -----------------------------
    def setup_camera(self):
        try:
            import cv2
            self.camera = cv2.VideoCapture(CAMERA_INDEX)
            if not self.camera.isOpened():
                print(f"⚠️ USB 카메라를 열 수 없습니다. CAMERA_INDEX={CAMERA_INDEX}")
                self.camera = None
                return
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print(f"✅ USB 카메라 준비 완료: index={CAMERA_INDEX}, {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
        except Exception as e:
            self.camera = None
            print(f"⚠️ 카메라 초기화 실패: {e}")

    def capture_image(self, path=None):
        if path is None:
            path = f"/tmp/robot_camera_{uuid.uuid4().hex}.jpg"
        if self.camera is None:
            raise RuntimeError("카메라가 준비되지 않았습니다.")

        import cv2
        frame = None
        ret = False
        for _ in range(3):
            ret, frame = self.camera.read()
        if not ret or frame is None:
            raise RuntimeError("USB 카메라에서 프레임을 읽지 못했습니다.")

        params = [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA_JPEG_QUALITY]
        cv2.imwrite(path, frame, params)
        print(f"📷 즉시 캡처 완료: {path}")
        return path

    # -----------------------------
    # Audio / STT
    # -----------------------------
    def _record_until_silence_wav(
        self,
        path,
        max_seconds=6.0,
        silence_after=0.8,
        wait_timeout=5.0,
        hard_limit_seconds=None,
        keep_recording_while_voice=True,
    ):
        chunk_bytes = int(AUDIO_SAMPLE_RATE * AUDIO_WIDTH_BYTES * AUDIO_CHANNELS * AUDIO_CHUNK_MS / 1000)
        cmd = [
            "arecord", "-q",
            "-D", AUDIO_DEVICE,
            "-f", "S16_LE",
            "-r", str(AUDIO_SAMPLE_RATE),
            "-c", str(AUDIO_CHANNELS),
            "-t", "raw",
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        frames = []
        pre_buffer = deque(maxlen=8)
        energies = []
        started = False
        start_time = None
        last_voice_time = None
        begin_wait = time.monotonic()
        threshold = AUDIO_MIN_ENERGY

        try:
            while True:
                data = proc.stdout.read(chunk_bytes)
                if not data:
                    break
                now = time.monotonic()
                energy = audioop.rms(data, AUDIO_WIDTH_BYTES)

                if not started:
                    pre_buffer.append(data)
                    energies.append(energy)
                    if len(energies) > 12:
                        energies.pop(0)
                    noise = max(1, sum(energies) / len(energies))
                    threshold = max(AUDIO_MIN_ENERGY, int(noise * AUDIO_NOISE_MULTIPLIER))

                    if AUDIO_DEBUG:
                        print(f"🎚️ energy={energy}, threshold={threshold}")

                    if energy > threshold:
                        started = True
                        start_time = now
                        last_voice_time = now
                        frames.extend(list(pre_buffer))
                        frames.append(data)
                    elif now - begin_wait > wait_timeout:
                        return None
                    continue

                frames.append(data)
                if energy > threshold:
                    last_voice_time = now

                elapsed = now - start_time

                # hard_limit_seconds는 정말 최종 안전 제한입니다.
                # 사용자가 계속 말하고 있어도 이 시간은 넘기지 않습니다.
                if hard_limit_seconds is not None and elapsed > hard_limit_seconds:
                    print(f"⏱️ 최대 녹음 시간 {hard_limit_seconds:.1f}초 도달")
                    break

                # max_seconds를 넘었더라도, 아직 말소리가 계속 감지되면 끊지 않습니다.
                if elapsed > max_seconds:
                    still_speaking = keep_recording_while_voice and (now - last_voice_time <= silence_after)
                    if not still_speaking:
                        break

                if now - last_voice_time > silence_after:
                    break
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=0.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        if not frames:
            return None

        with wave.open(path, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(AUDIO_WIDTH_BYTES)
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return path

    def listen_korean(
        self,
        max_seconds=6.0,
        silence_after=0.8,
        wait_timeout=5.0,
        hard_limit_seconds=None,
        keep_recording_while_voice=True,
    ):
        try:
            import speech_recognition as sr
        except Exception as e:
            print(f"❌ SpeechRecognition 라이브러리가 필요합니다: {e}")
            return ""

        audio_path = f"/tmp/robot_command_{uuid.uuid4().hex}.wav"
        try:
            print("🎤 듣는 중...")
            recorded = self._record_until_silence_wav(
                audio_path,
                max_seconds=max_seconds,
                silence_after=silence_after,
                wait_timeout=wait_timeout,
                hard_limit_seconds=hard_limit_seconds,
                keep_recording_while_voice=keep_recording_while_voice,
            )
            if not recorded:
                return ""
            recognizer = sr.Recognizer()
            with sr.AudioFile(recorded) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ko-KR").strip()
            print(f"🗣️ 인식된 말: {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"⚠️ 음성 인식 실패: {type(e).__name__}: {e}")
            return ""
        finally:
            try:
                Path(audio_path).unlink(missing_ok=True)
            except Exception:
                pass

    # -----------------------------
    # Speaker / TTS / Music
    # -----------------------------
    def _player_cmd(self, file_path):
        if shutil.which("mpg123"):
            return ["mpg123", "-q", str(file_path)]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)]
        return None

    def play_audio_file(self, file_path, timeout=None):
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"⚠️ 오디오 파일 없음: {file_path}")
            return False

        cmd = self._player_cmd(file_path)
        if cmd is None:
            print("⚠️ mp3 재생기가 없습니다. sudo apt install mpg123 를 실행하세요.")
            return False

        print(f"🎵 재생: {file_path}")
        try:
            subprocess.run(cmd, check=False, timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            print(f"⚠️ 오디오 재생 timeout({timeout}s). 다음 단계로 넘어갑니다.")
            return False
        except Exception as e:
            print(f"⚠️ 오디오 재생 실패: {e}")
            return False

    def speak(self, text):
        text = clean_tts_text(text)
        if not text:
            return
        print(f"🔊 로봇: {text}")
        if not USE_TTS:
            return

        try:
            from gtts import gTTS
            TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha1(text.encode("utf-8")).hexdigest()
            mp3_path = TTS_CACHE_DIR / f"{key}.mp3"
            if not mp3_path.exists():
                gTTS(text=text, lang="ko").save(str(mp3_path))

            # TTS는 중간에 끊지 않고 끝까지 재생합니다.
            # 꼭 제한이 필요할 때만 TTS_TIMEOUT_SEC 환경변수를 숫자로 지정하세요.
            timeout = None
            if str(TTS_TIMEOUT_SEC).strip():
                try:
                    timeout = float(TTS_TIMEOUT_SEC)
                except ValueError:
                    timeout = None
            self.play_audio_file(mp3_path, timeout=timeout)
        except Exception as e:
            print(f"⚠️ TTS 실패: {e}")

    def cleanup(self):
        self.stop_led_blink(force_message=False)
        self.command_led_off()
        self.stop_motors()
        if self.camera is not None:
            try:
                self.camera.release()
                print("📷 카메라 종료")
            except Exception:
                pass
        if self.gpio_ready:
            GPIO.cleanup()
            print("✅ GPIO cleanup 완료")
