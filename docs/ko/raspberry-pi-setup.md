# Raspberry Pi 설정

[English](../raspberry-pi-setup.md) | [한국어](raspberry-pi-setup.md)

이 문서는 Raspberry Pi OS에서 현재 공개된 Gemini function calling 예제를 실행하는 방법을 설명합니다. 아래 절차만으로 실제 모터가 움직이지는 않습니다. 공개 코드에는 GPIO, 실제 거리 센서 읽기, 카메라 입력과 마이크 명령 수집이 구현되어 있지 않습니다.

## 준비물과 범위

코드 흐름만 확인하려면 Raspberry Pi와 인터넷 연결, Gemini API 키, Python 환경이면 충분합니다. 음성 재생을 확인하려면 스피커 또는 USB 오디오 장치가 추가로 필요합니다.

실물 프로토타입에서 사용한 Raspberry Pi 5, 모터 드라이버, DC 모터, HC-SR04와 카메라는 현재 공개 예제를 실행하는 데 필수는 아닙니다. 장치를 연결해도 현재 코드가 제어하지 않습니다.

## 1. Raspberry Pi OS 준비

지원되는 64비트 Raspberry Pi OS를 설치하고 네트워크를 설정합니다. 원격 개발이 필요할 때만 SSH를 활성화합니다.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip alsa-utils
```

- `git`: 저장소 복제에 사용합니다.
- `python3-venv`: 프로젝트별 가상환경을 만듭니다.
- `python3-pip`: Python 패키지를 설치합니다.
- `alsa-utils`: `aplay`, `speaker-test`로 오디오 장치를 확인할 때 사용합니다.

Raspberry Pi OS 버전과 오디오 장치에 따라 추가 시스템 패키지가 필요할 수 있습니다. 현재 공개 코드에는 마이크 입력이 없으므로 PortAudio나 음성 인식 패키지는 필수가 아닙니다.

## 2. 저장소 복제

```bash
git clone https://github.com/cora1022/gemini-raspberry-pi-robot.git
cd gemini-raspberry-pi-robot
```

저장소 이름이 `robot`에서 `gemini-raspberry-pi-robot`으로 변경되었으므로 이전 clone 주소를 사용하지 않습니다.

## 3. Python 가상환경

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

터미널 프롬프트 앞에 `(.venv)`가 표시되는지 확인합니다. 새 터미널을 열었다면 프로젝트 폴더에서 `source .venv/bin/activate`를 다시 실행합니다.

## 4. requirements.txt 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 패키지는 다음과 같습니다.

- `google-genai`: `main_brain.py`의 Gemini 호출
- `google-generativeai`: 실행 불가능한 이전 실험 파일 `2main_brain.py`가 참조하는 SDK
- `python-dotenv`: `.env` 읽기
- `gTTS`: 한국어 음성 MP3 생성
- `pygame`: 생성한 음성 파일 재생

의존성은 최소 버전만 지정되어 있어 설치 시점에 따라 SDK 동작이 달라질 수 있습니다. 재현성이 중요하면 검증한 버전을 별도 환경에서 고정해야 합니다.

## 5. 환경변수 설정

```bash
cp .env.example .env
nano .env
```

```text
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
```

- `GOOGLE_API_KEY`에는 실제 키를 넣습니다.
- `GEMINI_MODEL`은 사용할 수 있는 모델명으로 바꿀 수 있습니다.
- `.env`는 `.gitignore`에 포함되어 있으나, 커밋 전에 `git status`로 다시 확인합니다.
- API 호출에는 인터넷 연결이 필요하며 할당량이나 비용이 발생할 수 있습니다.

## 6. 오디오 장치 확인

```bash
aplay -l
speaker-test -t wav -c 2
```

`actions.py`의 `speak`는 gTTS로 `speech.mp3`를 생성한 뒤 pygame으로 재생합니다. gTTS는 네트워크를 사용합니다. pygame 믹서 초기화나 재생에 실패하면 코드가 오류를 출력하고 계속 진행합니다.

음성 출력이 필요하지 않더라도 현재 코드는 모델이 텍스트만 반환하면 `speak`를 호출할 수 있습니다. 조용한 환경에서 테스트하거나 오디오 장치가 없는 경우 이 동작을 미리 고려하세요.

## 7. 현재 재현 가능한 예제 실행

```bash
python test_case.py
```

실행하면 세 개의 명령과 가상 거리 값이 Gemini API로 전달됩니다. 전진·회전·정지 함수가 선택되면 실제 모터 대신 콘솔에 동작 메시지가 출력됩니다. 음성 함수가 선택되거나 일반 텍스트 응답이 오면 음성 재생을 시도할 수 있습니다.

다음 명령은 테스트를 시작하지 않습니다.

```bash
python main_brain.py
```

`main_brain.py`에는 명령행 진입점이 없어 환경변수 확인과 클라이언트 생성, 함수 정의 후 종료됩니다.

`python 2main_brain.py`는 현재 `robot` 객체와 `move_backward`가 없어서 실행할 수 없습니다.

## 문제 확인

### `GOOGLE_API_KEY environment variable is required`

`.env`가 프로젝트 루트에 있는지, 변수명이 정확한지, 가상환경에서 `python-dotenv`가 설치되었는지 확인합니다.

### Gemini API 오류

인터넷 연결, API 키 상태, 모델 사용 가능 여부, 할당량을 확인합니다. `test_case.py`는 세 번의 실제 요청을 수행합니다.

### 오디오 오류

`aplay -l`로 장치가 보이는지 확인하고, HDMI·USB·아날로그 출력 중 운영체제가 선택한 기본 장치를 확인합니다. 오디오 오류는 이동 스텁의 실행 가능 여부와 별개입니다.

## 실제 하드웨어 연결 시 필요한 추가 구현

현재 공개 코드만으로는 모터, HC-SR04 또는 카메라가 동작하지 않습니다. 실물 장치를 사용하려면 최소한 다음 작업이 필요합니다.

- GPIO 라이브러리와 모터 드라이버 제어 구현
- HC-SR04 읽기와 타임아웃·이상값 처리
- 실제 센서 값을 사용하는 코드 수준 장애물 차단
- 함수명, 지속시간, 속도 등 모델 인자 검증
- 긴급 정지와 GPIO 정리 처리
- 카메라가 필요하면 프레임 캡처와 이미지 입력 경로 구현
- 가상 하드웨어 테스트를 통과한 뒤 바퀴를 띄운 상태에서 단계별 실물 검증

개념 배선과 최초 테스트 순서는 [배선 가이드](wiring.md)를 참고하세요.
