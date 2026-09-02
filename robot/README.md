# Raspberry Pi 로봇 에이전트

Raspberry Pi 5에서 모터, 초음파 센서, 카메라와 음성 장치를 제어하고 VPS와 통신하는 실행 애플리케이션입니다.

## 아키텍처

```text
bootstrap
  ├─ application     명령 직렬화, 안전정지, 음성 실행 흐름
  ├─ actions         한국어 명령 계획과 동작 오케스트레이션
  ├─ domain          명령, 상태와 계층 간 포트
  ├─ hardware        GPIO, 모터, 센서, 카메라와 오디오 어댑터
  ├─ infrastructure  VPS WebSocket과 gpsd 어댑터
  └─ intelligence    Gemini SDK 경계
```

`RobotHardware`와 `RobotActions`는 기존 호출 방식을 유지하는 파사드입니다. 모터 출력과 초음파 판정은 별도 장치 모듈에 있고 GPIO 초기화와 정리는 `GpioRuntime` 한 곳에서만 담당합니다. 원격 연결이 끊기거나 주행 lease가 만료되면 application controller가 모터를 정지합니다.

## 설치

저장소 루트에서 다음 명령을 실행합니다.

```bash
cd robot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

`.env`에 VPS 주소, 로봇 토큰과 필요한 API 키를 설정합니다. 실제 토큰과 API 키가 들어 있는 `.env`는 Git에 추가하지 않습니다.

## 실행과 테스트

```bash
robot-agent
python -m pytest
```

기존 `python main_brain.py` 실행도 호환됩니다. 상시 실행에는 `deploy/robot.service.example`을 사용합니다.

## 주요 안전장치

- 전진 전 HC-SR04 거리 확인
- 센서 비활성화 또는 측정 실패 시 실제 GPIO 환경에서 전진 차단
- 원격 주행 명령에 짧은 lease 적용
- 원격 연결 종료와 송신 timeout 시 안전정지
- 서버의 `hello_ack`와 프로토콜 버전을 확인한 뒤에만 온라인 전환
- 최신 영상 프레임만 유지하는 bounded 전송 버퍼
