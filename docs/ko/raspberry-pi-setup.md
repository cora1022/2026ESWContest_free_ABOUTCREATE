# Raspberry Pi 설정

[English](../raspberry-pi-setup.md) | [한국어](raspberry-pi-setup.md)

이 문서는 Raspberry Pi OS에서 현재 통합 코드를 준비하는 절차입니다. 실제 모터를 연결하기 전에 [배선 가이드](wiring.md)와 안전 주의사항을 먼저 확인하세요.

## 1. 운영체제와 시스템 패키지

64비트 Raspberry Pi OS를 준비하고 필요한 경우에만 SSH를 활성화합니다.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip alsa-utils mpg123 ffmpeg libgl1 libglib2.0-0
```

- `alsa-utils`: `arecord`, `aplay`, 오디오 장치 확인
- `mpg123`·`ffmpeg`: gTTS 음성 재생과 대체 재생 경로
- `libgl1`·`libglib2.0-0`: OpenCV 실행에 필요할 수 있는 시스템 라이브러리

Raspberry Pi OS 버전과 보드에 따라 GPIO 백엔드 호환성이 다를 수 있습니다. 이 코드는 `RPi.GPIO` 인터페이스를 사용하므로 설치 오류가 나면 사용 중인 보드·OS에 맞는 호환 패키지를 확인해야 합니다.

## 2. 저장소 복제와 가상환경

```bash
git clone https://github.com/cora1022/gemini-raspberry-pi-robot.git
cd gemini-raspberry-pi-robot

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

새 터미널을 열었다면 프로젝트 폴더에서 `source .venv/bin/activate`를 다시 실행합니다.

## 3. 환경변수

```bash
cp .env.example .env
nano .env
```

최소 설정은 다음과 같습니다.

```dotenv
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
```

실제 장치에 맞춰 다음 값을 확인합니다.

```dotenv
AUDIO_DEVICE=plughw:3,0
CAMERA_INDEX=1
SAFE_DISTANCE_CM=25
ULTRASONIC_STOP_CM=18
ULTRASONIC_TRIG=23
ULTRASONIC_ECHO=24
COMMAND_LED_PIN=25
```

`.env`는 커밋하지 않습니다. 실행 전 `git status --ignored`로 무시 상태를 확인하고, 키가 노출되었다면 파일 삭제보다 먼저 키를 폐기합니다.

## 4. 마이크와 스피커 확인

장치 번호를 찾습니다.

```bash
arecord -l
aplay -l
```

`.env`의 `AUDIO_DEVICE`와 같은 장치로 짧게 녹음합니다.

```bash
arecord -D plughw:3,0 -f S16_LE -r 48000 -c 1 -d 3 microphone-test.wav
aplay microphone-test.wav
speaker-test -t wav -c 2
```

장치 번호와 지원 샘플레이트는 환경마다 다릅니다. 음성 인식과 gTTS는 네트워크 연결에도 영향을 받습니다.

## 5. 카메라 확인

`CAMERA_INDEX`가 맞는지 OpenCV로 확인합니다.

```bash
python - <<'PY'
import cv2
camera = cv2.VideoCapture(1)
ok, frame = camera.read()
print("camera:", ok, None if frame is None else frame.shape)
camera.release()
PY
```

`False`가 나오면 `/dev/video*`와 USB 연결을 확인하고 index를 0, 1, 2 순서로 바꿔 봅니다.

## 6. 명령 계획만 시험하기

```bash
python test_case.py
```

이 스크립트는 GPIO, 카메라, 마이크, 모터 메서드를 호출하지 않습니다. API 키가 있으면 Gemini의 JSON 계획을 확인하고, 없으면 규칙 기반 대체 결과를 보여 줍니다. 하드웨어 안전 시험을 대신하지는 않습니다.

## 7. 실제 로봇 실행

배선, 바퀴를 띄운 모터 시험, 거리 센서 값을 모두 확인한 뒤 실행합니다.

```bash
python main_brain.py
```

프로그램은 호출어를 기다린 뒤 명령을 다시 듣습니다. 종료 시에는 `종료`, `끝내`, `그만` 같은 음성 명령을 사용하거나 `Ctrl+C`를 누릅니다. 종료 경로에서 모터 정지와 GPIO 정리를 시도하지만, 프로그램과 별개로 즉시 끌 수 있는 모터 전원 스위치를 준비하세요.

`python 2main_brain.py`는 현재 진입점이 아닙니다. 이 파일은 지금 저장소에 없는 `robot` 객체를 요구하는 이전 실험 기록이라 그대로 실행되지 않습니다.

## 최초 실물 시험 순서

1. 모터 전원을 분리한 채 GPIO와 센서 값을 확인합니다.
2. HC-SR04 ECHO에 5V가 직접 들어가지 않도록 분압 또는 레벨 변환을 확인합니다.
3. 바퀴를 바닥에서 띄웁니다.
4. API 없이 모터 방향과 정지만 짧게 확인합니다.
5. 장애물을 두고 25cm 전진 차단과 18cm 연속 주행 정지를 각각 확인합니다.
6. 센서를 분리하거나 ECHO 이상을 만들어 실패 시 정지 동작을 확인합니다.
7. 카메라·마이크·Gemini를 차례로 추가합니다.
8. 넓은 공간에서 낮은 속도와 짧은 명령으로 바닥 주행을 시작합니다.

## 자주 확인할 문제

- API 오류: 키, 모델 사용 가능 여부, 인터넷, 할당량을 확인합니다.
- 마이크 무응답: `AUDIO_DEVICE`, 샘플레이트, USB 장치 번호를 확인합니다.
- 카메라 실패: `CAMERA_INDEX`, `/dev/video*`, 다른 프로세스의 장치 점유를 확인합니다.
- GPIO 테스트 모드: `RPi.GPIO` 설치와 실행 보드가 Raspberry Pi인지 확인합니다.
- 로봇이 직진하지 않음: 코드뿐 아니라 배터리 전압, 모터 극성, 바닥 마찰과 좌우 모터 편차를 확인합니다.
