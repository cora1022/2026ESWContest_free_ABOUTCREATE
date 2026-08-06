# Raspberry Pi Setup

[English](raspberry-pi-setup.md) | [한국어](ko/raspberry-pi-setup.md)

This guide prepares Raspberry Pi OS for the public function-calling example. It does not turn the current repository into a motor controller: the public source has no GPIO driver, sensor read, camera input, or microphone command loop.

## 1. Prepare Raspberry Pi OS

Use a supported 64-bit Raspberry Pi OS release, configure networking, and enable SSH only if remote access is needed.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip alsa-utils
```

`alsa-utils` is useful for checking speaker devices. Additional audio packages can vary by Raspberry Pi OS release and connected hardware.

## 2. Clone and Install

```bash
git clone https://github.com/cora1022/gemini-raspberry-pi-robot.git
cd gemini-raspberry-pi-robot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Configure Gemini

```bash
nano .env
```

```text
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Do not commit the real `.env` file.

## 4. Check Audio

```bash
aplay -l
speaker-test -t wav -c 2
```

`actions.py` uses gTTS, which requires network access, and pygame, which requires a working output device. Audio errors are caught and printed, so a movement stub may still run even if speech playback fails.

## 5. Run the Current Example

```bash
python test_case.py
```

This command makes three live Gemini API requests with simulated distance values. It may consume API quota. It does not read a physical ultrasonic sensor or move a motor.

Do not use `python main_brain.py` as an expected test entrypoint. The file defines `decide_and_act` but does not call it when executed directly.

## Hardware Integration Is Additional Work

To control a physical robot, add and test a hardware adapter, sensor reads, deterministic safety checks, GPIO cleanup, an emergency stop, and failure handling. The example GPIO map in the wiring guide is conceptual and is not referenced by the current Python source.
