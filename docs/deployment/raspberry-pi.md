# Raspberry Pi 배포

이 문서는 전체 모노레포를 Raspberry Pi에 checkout하고 `robot` 애플리케이션만 별도 가상환경에서 실행하는 기준 절차입니다.

## 고정 경로

| 항목 | 경로 |
|---|---|
| 저장소 루트 | `/home/dslab/Desktop/robot-pj` |
| 애플리케이션 | `/home/dslab/Desktop/robot-pj/robot` |
| 가상환경 | `/home/dslab/Desktop/robot-pj/robot/.venv` |
| 환경 파일 | `/home/dslab/Desktop/robot-pj/robot/.env` |
| 실행 명령 | `/home/dslab/Desktop/robot-pj/robot/.venv/bin/robot-agent` |
| systemd unit | `/etc/systemd/system/robot.service` |

경로와 사용자 이름이 서비스 파일과 다르면 서비스가 시작되더라도 소스, `.env` 또는 가상환경을 찾지 못합니다. 다른 경로를 사용하려면 unit의 `User`, `WorkingDirectory`, `EnvironmentFile`과 `ExecStart`를 함께 변경합니다.

## 1. 물리적 안전 상태

최초 설치와 하드웨어 변경 직후에는 다음 상태에서 시작합니다.

1. 바퀴를 바닥에서 띄웁니다.
2. L298N의 8V 모터 전원을 분리합니다.
3. Raspberry Pi와 L298N의 공통 GND는 유지합니다.
4. 모터 전원을 즉시 끊을 수 있는 위치에서 작업합니다.
5. HC-SR04 ECHO에 3.3V 레벨 변환이 적용됐는지 확인합니다.

## 2. OS 준비

```bash
sudo apt update
sudo apt install -y \
  git python3-venv python3-dev build-essential \
  portaudio19-dev libasound2-dev alsa-utils \
  ffmpeg mpg123 libgl1 libglib2.0-0 v4l-utils curl

sudo usermod -aG gpio,audio,video,dialout dslab
```

그룹을 처음 추가했다면 로그아웃 후 다시 로그인하거나 재부팅합니다.

```bash
id dslab
```

GNSS를 실제로 사용할 때만 `gpsd`와 `gpsd-clients`를 추가합니다. 현재 대시보드에는 위치 화면이 없습니다.

## 3. 저장소 준비

비공개 저장소를 읽을 수 있는 SSH deploy key 또는 사용자 인증을 먼저 구성합니다. 토큰을 clone URL에 직접 넣지 않습니다.

```bash
cd /home/dslab/Desktop
git clone <PRIVATE_REPOSITORY_URL> robot-pj
cd /home/dslab/Desktop/robot-pj
git status --short --branch
```

이미 저장소가 있다면 로컬 변경을 먼저 확인합니다.

```bash
cd /home/dslab/Desktop/robot-pj
git status --short --branch
git pull --ff-only
```

장비의 `.env`는 Git에서 관리하지 않으므로 pull 전에 삭제하거나 덮어쓰지 않습니다.

## 4. 애플리케이션 설치

공통 프로토콜과 로봇 패키지를 같은 가상환경에 설치합니다.

```bash
cd /home/dslab/Desktop/robot-pj
python3 -m venv robot/.venv
robot/.venv/bin/python -m pip install --upgrade pip setuptools wheel
robot/.venv/bin/python -m pip install ./packages/robot-protocol ./robot
```

Raspberry Pi 5에서는 `import RPi.GPIO as GPIO` 호환 구현으로 `rpi-lgpio`를 사용합니다. 설치 후 실제 distribution을 확인합니다.

```bash
robot/.venv/bin/python -m pip show rpi-lgpio
robot/.venv/bin/python -c "import RPi.GPIO as GPIO; print(GPIO.VERSION)"
```

`RPi.GPIO`와 `rpi-lgpio`를 같은 환경에 중복 설치하지 않습니다.

## 5. 환경 파일

```bash
cd /home/dslab/Desktop/robot-pj/robot
test -f .env || cp .env.example .env
chmod 600 .env
```

최소 설정은 다음과 같습니다.

```dotenv
ROBOT_ID=robot-01
ROBOT_SERVER_URL=wss://<VPS_HOST>/ws/robot
ROBOT_TOKEN=<VPS와_동일한_긴_무작위_값>
REMOTE_ENABLED=1
```

운영 장치에서 확인된 USB 이름을 사용하면 재연결 후 카드 번호가 바뀌어도 같은 장치를 찾을 수 있습니다.

```dotenv
AUDIO_DEVICE=plughw:CARD=CAMERA,DEV=0
AUDIO_OUTPUT_DEVICE=plughw:CARD=UACDemoV10,DEV=0
CAMERA_INDEX=0
```

HC-SR04 배선과 다회 측정이 끝나기 전에는 다음처럼 비활성화합니다.

```dotenv
ULTRASONIC_ENABLED=0
```

실제 Raspberry Pi에서는 이 상태를 안전거리 0cm로 취급하므로 전진이 차단됩니다.

## 6. 모터 전원 없는 첫 실행

```bash
cd /home/dslab/Desktop/robot-pj/robot
.venv/bin/robot-agent
```

다른 터미널에서 VPS 상태를 확인합니다.

```bash
curl -fsS https://<VPS_HOST>/health
```

`status=ok`와 `robot_online=true`를 확인한 뒤 `Ctrl+C`로 종료합니다. 토큰이나 `.env` 전체를 로그에 출력하지 않습니다.

## 7. systemd 등록

저장소의 unit을 설치하고 실제 내용을 한 번 확인합니다.

```bash
cd /home/dslab/Desktop/robot-pj
sudo install -m 0644 robot/deploy/robot.service.example /etc/systemd/system/robot.service
sudo systemctl daemon-reload
sudo systemctl enable --now robot.service
sudo systemctl --no-pager --full status robot.service
```

로그는 다음과 같이 확인합니다.

```bash
journalctl -u robot.service -n 100 --no-pager
journalctl -u robot.service -f
```

## 8. 이후 업데이트

서비스가 GPIO와 카메라를 점유하므로 업데이트 중에는 먼저 중지합니다.

```bash
cd /home/dslab/Desktop/robot-pj
git status --short --branch
sudo systemctl stop robot.service
git pull --ff-only
robot/.venv/bin/python -m pip install ./packages/robot-protocol ./robot
sudo systemctl start robot.service
systemctl is-active robot.service
curl -fsS https://<VPS_HOST>/health
```

`git status`에 예상하지 못한 수정이 있으면 덮어쓰지 않고 원인을 확인합니다. 프로토콜 호환성 변경이 포함된 경우 [VPS 배포](vps.md)의 순서에 따라 VPS를 먼저 배포합니다.

## 9. 물리 시험 승인 단계

다음 시험은 자동 배포에 포함하지 않습니다.

- HC-SR04 다회 거리 측정
- 교정된 전진, 후진, 좌회전과 우회전
- 브라우저에서 실제 원격 주행

시험 전 [하드웨어 안전 조건](../hardware.md)을 확인하고, 한 동작을 한 번 실행한 뒤 GPIO가 모두 LOW로 정리됐는지 검증합니다.

## 완료 기준

- `robot.service`가 `enabled`와 `active` 상태입니다.
- VPS `/health`가 `robot_online=true`를 반환합니다.
- `.env` 권한이 600이며 Git 추적 대상이 아닙니다.
- 카메라와 오디오 장치를 이름 기반으로 찾습니다.
- 승인하지 않은 모터 동작이 실행되지 않았습니다.
