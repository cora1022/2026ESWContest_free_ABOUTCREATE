# Raspberry Pi Setup

[English](raspberry-pi-setup.md) | [한국어](ko/raspberry-pi-setup.md)

This guide prepares the restored integrated runtime on Raspberry Pi OS. Read the [wiring guide](wiring.md) before connecting motor power.

## System packages

Use a supported 64-bit Raspberry Pi OS image.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip alsa-utils mpg123 ffmpeg libgl1 libglib2.0-0
```

Board and OS versions can affect GPIO backend compatibility. The code imports the `RPi.GPIO` interface; if installation fails, check the compatible package for your board and OS rather than forcing an unverified driver.

## Clone and install

```bash
git clone https://github.com/cora1022/gemini-raspberry-pi-robot.git
cd gemini-raspberry-pi-robot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Environment

```bash
cp .env.example .env
nano .env
```

Set at least:

```dotenv
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Then verify device-specific values such as `AUDIO_DEVICE`, `CAMERA_INDEX`, GPIO pins, `SAFE_DISTANCE_CM`, and `ULTRASONIC_STOP_CM`. Never commit `.env`.

## Audio checks

```bash
arecord -l
aplay -l
arecord -D plughw:3,0 -f S16_LE -r 48000 -c 1 -d 3 microphone-test.wav
aplay microphone-test.wav
```

Replace the device name with the one reported on your system. Speech recognition and gTTS require network access.

## Camera check

```bash
python - <<'PY'
import cv2
camera = cv2.VideoCapture(1)
ok, frame = camera.read()
print("camera:", ok, None if frame is None else frame.shape)
camera.release()
PY
```

Try other indices and inspect `/dev/video*` if capture fails.

## Planning-only check

```bash
python test_case.py
```

This script does not call GPIO, camera, microphone, or motor methods. With an API key it prints Gemini JSON plans; without a key it exercises the rule fallback. It is not a physical safety test.

## Physical runtime

Only after wiring and raised-wheel tests:

```bash
python main_brain.py
```

The program listens for a Korean wake phrase, captures a command, and dispatches allowed actions. Keep the motor power switch within reach. `2main_brain.py` is a legacy experiment that expects a missing `robot` object and is not runnable as the current entrypoint.

## First hardware test order

1. Verify wiring and sensor readings with motor power disconnected.
2. Confirm HC-SR04 ECHO voltage conversion.
3. Raise the wheels off the floor.
4. Test motor direction and stop without Gemini.
5. Verify the 25 cm forward guard and 18 cm continuous-motion stop.
6. Exercise sensor fault conditions.
7. Add camera, microphone, and Gemini one layer at a time.
8. Begin short, low-speed floor tests in an open area.

Battery voltage, motor polarity, floor friction, USB device numbering, and network latency can all affect behavior even when the Python process runs normally.
