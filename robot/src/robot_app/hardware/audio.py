from __future__ import annotations

import audioop
import hashlib
import re
import shutil
import subprocess
import time
import uuid
import wave
from collections import deque
from pathlib import Path
from typing import Callable

from robot_app.config import AudioSettings


SpeechListener = Callable[[str, bytes | None, str], None]


def clean_tts_text(text: object) -> str:
    """Remove markup and action notes before passing text to TTS."""
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"^\s*[-•]\s*", "", value, flags=re.MULTILINE)
    for char in ['*', '"', "'", "“", "”", "‘", "’", "「", "」", "『", "』"]:
        value = value.replace(char, "")
    value = re.sub(
        r"\([^)]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^)]*\)",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\[[^\]]*(?:재생|mp3|wav|파일|카메라|촬영|분석|동작|행동)[^\]]*\]",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", value).strip()


class SpeechAudio:
    """ALSA recording, speech recognition, playback and TTS adapter."""

    def __init__(self, settings: AudioSettings, initialize: bool = True) -> None:
        self.settings = settings
        self.input_ok: bool | None = None
        self.output_ok: bool | None = None
        self._listener: SpeechListener | None = None
        self._retry_after = 0.0
        self._error_last_logged = 0.0
        if initialize:
            self.setup()

    def set_speech_listener(self, listener: SpeechListener | None) -> None:
        self._listener = listener

    def setup(self) -> None:
        self.input_ok = self._alsa_device_available("arecord", self.settings.input_device, "input")
        if self.settings.output_device:
            self.output_ok = self._alsa_device_available("aplay", self.settings.output_device, "output")

    def _alsa_device_available(self, command: str, device: str, direction: str) -> bool:
        executable = shutil.which(command)
        if not executable:
            self._audio_error(direction, f"{command} 명령을 찾을 수 없습니다")
            return False
        try:
            result = subprocess.run(
                [executable, "-L"],
                check=False,
                timeout=3.0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
            self._audio_error(direction, exc)
            return False
        if result.returncode != 0:
            self._audio_error(direction, result.stderr or f"{command} -L 종료 코드 {result.returncode}")
            return False
        if device not in result.stdout:
            self._audio_error(direction, f"ALSA 목록에서 {device} 장치를 찾을 수 없습니다")
            return False
        print(f"✅ 오디오 {direction} 장치 확인: {device}")
        return True

    def _audio_error(self, direction: str, detail: object) -> None:
        now = time.monotonic()
        if direction == "input":
            self.input_ok = False
            self._retry_after = now + self.settings.error_backoff_sec
        else:
            self.output_ok = False
        if now - self._error_last_logged < self.settings.error_log_interval_sec:
            return
        self._error_last_logged = now
        summary = re.sub(r"\s+", " ", str(detail or "알 수 없는 오류")).strip()[:240]
        print(f"⚠️ 오디오 {direction} 장치 오류: {summary}")

    def _wait_for_audio_retry(self) -> bool:
        remaining = self._retry_after - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(remaining)
        return True

    def record_until_silence_wav(
        self,
        path: str,
        max_seconds: float = 6.0,
        silence_after: float = 0.8,
        wait_timeout: float = 5.0,
        hard_limit_seconds: float | None = None,
        keep_recording_while_voice: bool = True,
    ) -> str | None:
        settings = self.settings
        chunk_bytes = int(
            settings.sample_rate
            * settings.width_bytes
            * settings.channels
            * settings.chunk_ms
            / 1000
        )
        command = [
            "arecord",
            "-q",
            "-D",
            settings.input_device,
            "-f",
            "S16_LE",
            "-r",
            str(settings.sample_rate),
            "-c",
            str(settings.channels),
            "-t",
            "raw",
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as exc:
            self._audio_error("input", exc)
            return None

        frames: list[bytes] = []
        pre_buffer: deque[bytes] = deque(maxlen=8)
        energies: list[int] = []
        started = False
        start_time: float | None = None
        last_voice_time: float | None = None
        begin_wait = time.monotonic()
        threshold = settings.min_energy

        try:
            while True:
                data = process.stdout.read(chunk_bytes)
                if not data:
                    return_code = process.poll()
                    if return_code not in (None, 0):
                        error = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
                        self._audio_error("input", error or f"arecord 종료 코드 {return_code}")
                    break
                self.input_ok = True
                self._retry_after = 0.0
                now = time.monotonic()
                energy = audioop.rms(data, settings.width_bytes)

                if not started:
                    pre_buffer.append(data)
                    energies.append(energy)
                    if len(energies) > 12:
                        energies.pop(0)
                    noise = max(1, sum(energies) / len(energies))
                    threshold = max(settings.min_energy, int(noise * settings.noise_multiplier))
                    if settings.debug:
                        print(f"🎚️ energy={energy}, threshold={threshold}")
                    if energy > threshold:
                        started = True
                        start_time = now
                        last_voice_time = now
                        frames.extend(pre_buffer)
                        frames.append(data)
                    elif now - begin_wait > wait_timeout:
                        return None
                    continue

                frames.append(data)
                if energy > threshold:
                    last_voice_time = now
                elapsed = now - start_time
                if hard_limit_seconds is not None and elapsed > hard_limit_seconds:
                    print(f"⏱️ 최대 녹음 시간 {hard_limit_seconds:.1f}초 도달")
                    break
                if elapsed > max_seconds:
                    still_speaking = keep_recording_while_voice and now - last_voice_time <= silence_after
                    if not still_speaking:
                        break
                if now - last_voice_time > silence_after:
                    break
        finally:
            try:
                process.terminate()
                process.wait(timeout=0.5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

        if not frames:
            return None
        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(settings.channels)
            wav_file.setsampwidth(settings.width_bytes)
            wav_file.setframerate(settings.sample_rate)
            wav_file.writeframes(b"".join(frames))
        return path

    def listen_korean(
        self,
        max_seconds: float = 6.0,
        silence_after: float = 0.8,
        wait_timeout: float = 5.0,
        hard_limit_seconds: float | None = None,
        keep_recording_while_voice: bool = True,
    ) -> str:
        try:
            import speech_recognition as sr
        except Exception as exc:
            print(f"❌ SpeechRecognition 라이브러리가 필요합니다: {exc}")
            return ""

        audio_path = f"/tmp/robot_command_{uuid.uuid4().hex}.wav"
        try:
            if self._wait_for_audio_retry():
                return ""
            print("🎤 듣는 중...")
            recorded = self.record_until_silence_wav(
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
        except Exception as exc:
            print(f"⚠️ 음성 인식 실패: {type(exc).__name__}: {exc}")
            return ""
        finally:
            try:
                Path(audio_path).unlink(missing_ok=True)
            except Exception:
                pass

    def player_command(self, file_path: str | Path) -> list[str] | None:
        if shutil.which("mpg123"):
            command = ["mpg123", "-q"]
            if self.settings.output_device:
                command.extend(["-a", self.settings.output_device])
            return [*command, str(file_path)]
        if shutil.which("ffplay"):
            return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)]
        return None

    def play_audio_file(self, file_path: str | Path, timeout: float | None = None) -> bool:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️ 오디오 파일 없음: {path}")
            return False
        command = self.player_command(path)
        if command is None:
            print("⚠️ mp3 재생기가 없습니다. sudo apt install mpg123 를 실행하세요.")
            return False
        print(f"🎵 재생: {path}")
        try:
            completed = subprocess.run(
                command,
                check=False,
                timeout=timeout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if completed.returncode != 0:
                self._audio_error("output", completed.stderr or f"재생기 종료 코드 {completed.returncode}")
                return False
            self.output_ok = True
            return True
        except subprocess.TimeoutExpired:
            print(f"⚠️ 오디오 재생 timeout({timeout}s). 다음 단계로 넘어갑니다.")
            return False
        except Exception as exc:
            print(f"⚠️ 오디오 재생 실패: {exc}")
            return False

    def speak(self, text: object) -> None:
        value = clean_tts_text(text)
        if not value:
            return
        print(f"🔊 로봇: {value}")
        if not self.settings.use_tts:
            self._notify_speech(value)
            return

        notified = False
        try:
            from gtts import gTTS

            self.settings.tts_cache_dir.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha1(value.encode("utf-8")).hexdigest()
            mp3_path = self.settings.tts_cache_dir / f"{key}.mp3"
            if not mp3_path.exists():
                gTTS(text=value, lang="ko").save(str(mp3_path))
            self._notify_speech(value, mp3_path.read_bytes(), "audio/mpeg")
            notified = True
            timeout = None
            if self.settings.tts_timeout_sec:
                try:
                    timeout = float(self.settings.tts_timeout_sec)
                except ValueError:
                    timeout = None
            self.play_audio_file(mp3_path, timeout=timeout)
        except Exception as exc:
            print(f"⚠️ TTS 실패: {exc}")
            if not notified:
                self._notify_speech(value)

    def _notify_speech(
        self,
        text: str,
        audio_bytes: bytes | None = None,
        audio_content_type: str = "audio/mpeg",
    ) -> None:
        if not self._listener:
            return
        try:
            self._listener(text, audio_bytes, audio_content_type)
        except Exception as exc:
            print(f"⚠️ 프론트 음성 자막 전달 실패: {exc}")
