# ADR 0002. VPS 중계에 WebSocket을 사용한다

- 상태: 승인
- 날짜: 2026-09-02

## 배경

방향 명령과 STOP은 짧은 지연으로 Pi에 도달해야 하고, Pi의 상태, 영상과 발화도 브라우저에 연속 전달해야 합니다. Raspberry Pi에 공개 포트를 열지 않고 NAT 환경에서 동작해야 합니다.

## 결정

Pi가 VPS의 `/ws/robot`으로 인증된 WSS 연결을 먼저 만듭니다. 브라우저는 HTTPS 로그인 후 `/ws/dashboard`에 연결합니다. FastAPI VPS가 명령과 상태를 양방향으로 중계하고 Nginx가 TLS를 종료합니다.

## 검토한 대안

- 짧은 HTTP polling은 구현이 단순하지만 명령과 영상에 불필요한 지연과 요청 비용이 생깁니다.
- MQTT는 reconnect와 QoS가 강점이지만 별도 broker 운영과 웹 인증 통합 범위가 커집니다.
- WebRTC는 영상에 유리하지만 제어 메시지, NAT traversal과 운영 복잡도가 현재 규모보다 큽니다.

## 결과

하나의 기술로 제어와 상태를 처리하고 Pi에는 outbound 연결만 필요합니다. 반면 connection lifecycle, backpressure와 ping timeout을 애플리케이션이 관리해야 합니다. 현재 Hub가 프로세스 메모리에 있으므로 VPS는 worker 1개로 실행합니다.
