# Raspberry Pi 로봇 프로젝트 인수인계

> 이 문서는 2026-09-01 운영 장비 점검 당시의 기록입니다. 이후 소스가 `robot`, `server`와 `packages/robot-protocol` 구조로 재편됐으므로 여기에 적힌 branch, 파일과 설치 경로를 현재 배포 명령으로 사용하지 않습니다. 현재 절차는 [Raspberry Pi 배포](deployment/raspberry-pi.md)와 [하드웨어 문서](hardware.md)를 따릅니다.

작성 기준일: 2026-09-01 (Europe/London)

## 1. 현재 운영 상태

- 프로젝트 경로: `/home/dslab/Desktop/robot-pj`
- Raspberry Pi: Raspberry Pi 5
- Git 브랜치: `master` (`origin/master` 추적)
- `robot.service`: `enabled`, `active`
- VPS: `https://181.214.136.80`
- VPS `/health`: `status=ok`, `robot_online=true`
- 모터 GPIO는 마지막 직접 시험 후 모두 LOW로 정리했다.
- 테스트 임시 사진, 녹음 및 로그 파일은 삭제했다.

## 2. 비밀값과 `.env`

- `.env`가 존재하며 권한은 `600`이다.
- `ROBOT_TOKEN`은 설정돼 있고 길이는 정확히 64자다.
- 실제 토큰이나 API 키는 이 문서에 기록하지 않았다.
- 비밀값을 Git에 추가하거나 GitHub에 푸시하지 않는다.
- 테스트에 필요한 서버 외부로 비밀값을 전송하지 않는다.

현재 확인된 비밀값 이외 설정:

```dotenv
REMOTE_ENABLED=1
CAMERA_INDEX=0
AUDIO_DEVICE=plughw:4,0
AUDIO_OUTPUT_DEVICE=plughw:3,0
AUDIO_SAMPLE_RATE=48000
```

기존 `.env`의 다른 항목은 보존돼 있다.

## 3. 카메라와 오디오

호스트 기준 장치는 정상 감지됐다.

- USB 웹캠: Realtek `0bda:5856 HD WEB CAMERA`
- 영상 노드: `/dev/video0`, `/dev/video1`
- `v4l2-ctl`에서 `/dev/video0` 웹캠 확인
- `rpicam-hello --list-cameras`: CSI 카메라는 없음
  - 현재 카메라는 USB UVC 장치이므로 이 결과는 USB 카메라 장애가 아니다.
- 웹캠 마이크: ALSA 캡처 카드 4 (`plughw:4,0`)
- USB 오디오 출력: ALSA 재생 카드 3 (`plughw:3,0`)
- 현재 사용자 `dslab`은 `gpio`, `audio`, `video` 그룹에 포함돼 있다.

완료된 실제 장치 시험:

- `/dev/video0` 사진 촬영 성공
- `plughw:4,0`에서 48 kHz, 모노, 3초 녹음 성공
- 승인 후 `plughw:3,0` 스피커 재생 성공
- 시험 파일은 모두 삭제 완료

커널 로그에는 USB 허브 장치들의 분리와 재연결, 디스크립터 오류 `-32`가 한 차례 있었다. 장치가 간헐적으로 끊기면 USB 허브 전원, 케이블, 접촉 상태를 먼저 확인한다.

## 4. 모터 배선과 방향 매핑

L298N 핀은 BCM 기준 다음과 같다.

| 신호 | GPIO |
|---|---:|
| IN1 | 5 |
| IN2 | 6 |
| IN3 | 16 |
| IN4 | 26 |

기존 코드에서 관찰된 실제 동작:

| 명령 | 기존 실제 동작 |
|---|---|
| 전진 | 우회전 |
| 후진 | 좌회전 |
| 좌회전 | 전진 |
| 우회전 | 후진 |

이 관찰에 맞춰 코드 매핑을 다음처럼 교정했다.

| 명령 | IN1 | IN2 | IN3 | IN4 |
|---|---:|---:|---:|---:|
| 전진 | 0 | 1 | 1 | 0 |
| 후진 | 1 | 0 | 0 | 1 |
| 좌회전 | 0 | 1 | 0 | 1 |
| 우회전 | 1 | 0 | 1 | 0 |
| 정지 | 0 | 0 | 0 | 0 |

변경 파일:

- `hardware.py`
  - 원격 연속 주행 매핑
  - 시간제 전진, 후진, 좌회전과 우회전
  - 장애물 감지 전진
- `tools/l298n_drive_test.py`
  - 전진과 후진 진단 매핑

교정된 매핑은 GPIO를 사용하지 않는 테스트 더블로 검증했다. 서비스도 변경 후 재시작했다. 다만 교정 후 네 방향을 실제 모터로 다시 확인하지는 않았다.

## 5. 테스트 결과

| 테스트 | 결과 |
|---|---|
| 프로젝트 import (`actions`, `robot_core`, `server`) | 성공 |
| 프로젝트 루트에서 `python -m pytest` | 9개 통과 |
| 방향 변경 후 비하드웨어 핀 매핑 검증 | 성공 |
| 방향 변경 후 전체 pytest 재검증 | 서버 WebSocket 테스트 구간에서 20초 제한 초과 |
| GPIO 모듈 import 및 Raspberry Pi 정보 | 성공 |
| HC-SR04 다회 거리값 확인 | 미완료 |
| 기존 매핑에서 직접 전진 0.5초 | 1회 실행 성공, 이후 GPIO LOW 정리 |
| 교정된 네 방향 실제 확인 | 미실행 |
| 전체 `tools/l298n_drive_test.py` | 미실행 |
| 원격 STOP 및 네 방향 주행 | 미완료 |
| 원격 카메라 촬영과 상태 전송 | 미완료 |
| 음성 호출어와 명령 인식 | 미완료 |

첫 `pytest` 실패는 `pytest` 실행 파일을 직접 호출했을 때의 import 경로 문제였으며, 프로젝트 루트에서 `python -m pytest`로 실행했을 때 9개가 통과했다. 방향 변경 뒤 재검증에서는 테스트 6개 이후 서버 WebSocket 테스트가 제한 시간에 걸렸다. 방향 변경 자체와 무관한 서버 테스트 구간이므로 별도 진단이 필요하다.

## 6. HC-SR04 및 원격 시험 주의사항

- HC-SR04 기본 핀: TRIG=`GPIO23`, ECHO=`GPIO24`
- 로컬 `.env`에는 `DASHBOARD_KEY`가 없어 VPS API로 거리 텔레메트리를 조회하지 못했다.
- HC-SR04 거리값을 여러 번 정상 확인하기 전에는 원격 전진 시험을 진행하지 않는 것이 안전하다.
- 센서가 `0cm`, 누락, 고정값 또는 타임아웃 상태면 원격 주행을 중단한다.
- 전진 로직은 안전거리 이하에서 자동으로 전진을 거부하도록 구현돼 있다.

## 7. 다음 물리 시험 전 필수 조건

모터를 움직이기 전에 사용자에게 다음을 다시 확인받는다.

1. 바퀴가 바닥에서 완전히 떠 있는지
2. 8V 모터 전원을 즉시 분리할 수 있는지
3. Raspberry Pi와 L298N 공통 GND가 유지되는지
4. ENA와 ENB 점퍼, IN1~IN4 배선 상태
5. 주변에 사람, 케이블, 장애물이 없는지

`robot.service`가 실행 중이면 GPIO가 점유돼 별도 테스트에서 `GPIO busy`가 발생한다. 물리 모터 시험은 다음 순서로 진행한다.

1. `robot.service` 중지
2. `inactive` 확인
3. 승인된 모터 동작을 정확히 한 번 실행
4. `finally`에서 IN1~IN4를 모두 LOW로 설정하고 GPIO 정리
5. `robot.service` 재시작
6. `active` 및 VPS `robot_online=true` 확인

방향이 예상과 달라도 코드나 배선을 자동으로 다시 변경하지 말고 실제 동작을 기록해 사용자에게 보고한다.

## 8. Git 작업 상태

현재 추적 중인 수정 파일:

```text
M hardware.py
M tools/l298n_drive_test.py
```

이 인수인계 문서 `RASPBERRY_PI_HANDOFF.md`는 새 파일이다. 변경 사항은 아직 Git 커밋이나 푸시를 하지 않았다.
