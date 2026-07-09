# Raspberry Pi Setup

This guide prepares a Raspberry Pi 5 or Raspberry Pi 4 for the robot control experiment.

## Hardware Checklist

- Raspberry Pi 5 or Raspberry Pi 4
- microSD card, 32 GB or larger
- USB microphone or ReSpeaker-style mic
- Speaker or 3.5 mm / USB audio output
- Motor driver such as L298N, TB6612FNG, or a compatible H-bridge
- Two DC motors or a small robot chassis
- Ultrasonic distance sensor such as HC-SR04
- Optional camera module or USB webcam
- Separate motor battery pack
- Common ground between Raspberry Pi, motor driver, and sensors

## OS Preparation

1. Install Raspberry Pi OS 64-bit.
2. Enable SSH if remote development is needed.
3. Update packages.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git portaudio19-dev
```

## Project Setup

```bash
git clone https://github.com/cora1022/robot.git
cd robot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `GOOGLE_API_KEY`.

```bash
nano .env
```

## Audio Check

Check microphone and speaker devices before connecting robot logic.

```bash
arecord -l
aplay -l
speaker-test -t wav -c 2
```

## Run

```bash
source .venv/bin/activate
python main_brain.py
```

## Safety Notes

- Keep motors powered from a separate battery pack.
- Share ground between the Pi and the motor driver.
- Do not power motors from the Raspberry Pi 5V pin.
- Test movement with wheels lifted before placing the robot on the floor.
- Keep `GOOGLE_API_KEY` in `.env` only and never commit it.
