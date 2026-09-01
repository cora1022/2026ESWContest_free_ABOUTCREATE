# robot-protocol

Raspberry Pi 로봇과 VPS 서버가 함께 사용하는 메시지 계약 패키지입니다. JSON 메시지 종류, 허용 명령, 프로토콜 버전과 바이너리 프레임 형식을 한 곳에서 관리합니다.

런타임 의존성이 없으며 Python 표준 라이브러리만 사용합니다.

## 설치

저장소 루트에서 다음과 같이 설치합니다.

```bash
python -m pip install ./packages/robot-protocol
```

개발 중에는 editable 설치를 사용할 수 있습니다.

```bash
python -m pip install -e ./packages/robot-protocol
```

## 공개 API

```python
from robot_protocol import ALLOWED_ACTIONS, PROTOCOL_VERSION
from robot_protocol.actions import Action, parse_action
from robot_protocol.messages import CommandMessage, HelloAckMessage, HelloMessage, MessageType
from robot_protocol.transport import pack_binary_event, unpack_binary_event
```

`RBT1` 바이너리 프레임은 JSON 메타데이터와 이미지 같은 바이트 페이로드를 하나의 WebSocket 바이너리 메시지로 묶습니다.

## 테스트

```bash
python -m pip install -e '.[test]'
python -m pytest
```

`pyproject.toml`에 `src` 경로와 테스트 디렉터리가 설정돼 있어 패키지 디렉터리에서 바로 실행할 수 있습니다.
