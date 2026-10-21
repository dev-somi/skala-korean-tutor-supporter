# ADR-0006: SSE 경로 — Vue → Spring(WebMVC SseEmitter) → FastAPI
- 상태: Accepted (2026-10-19)
- 관련 모듈: `frontend/src/api/sse.ts`, `backend/aiclient`, `ai-server` 스트리밍 엔드포인트

## 배경 (Context)
채팅 답변과 그래프 진행 상황(노드 시작·종료, 검토 대기)을 실시간으로 보여 줘야 한다. 서버 → 클라이언트 단방향이라 SSE를 쓴다(참고노트 2장 #4).
그래프는 FastAPI에서 돌고, 시간 측정·결과 저장은 Spring이 해야 한다(ADR-0001, 0005).

## 결정 (Decision)
- 브라우저는 **Spring만** 호출한다.
- Spring(WebMVC)은 `WebClient`로 FastAPI SSE를 받아(`bodyToFlux(ServerSentEvent)`) `SseEmitter`로 다시 내보낸다. 중간에 `done` 이벤트를 보면 결과를 DB에 저장하고 TimeLog를 닫는다.
- `spring-boot-starter-webflux`는 WebClient용으로만 넣고 서버는 MVC로 둔다.
- 헤더 `X-Accel-Buffering: no`, `Cache-Control: no-cache`를 양쪽에 둔다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| Spring WebFlux로 전환 | 서버 전체를 리액티브로 | Flux를 그대로 흘려보내 SSE 프록시가 자연스럽다 | JPA(블로킹)와 섞어 쓰기 어렵고 학습 부담이 크다 |
| Vue가 FastAPI SSE를 직접 구독 | Spring을 거치지 않음 | 가장 단순하다 | 진입점이 두 개가 되고(CORS, 주소 관리), 진행 중에 Spring이 결과 저장·시간 측정을 할 수 없다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 프론트는 서버 주소 하나만 안다. 시간 측정과 결과 저장이 스트림 안에서 자연스럽게 일어난다.
- 대가: SSE 연결마다 Spring 스레드 하나를 오래 잡는다(단일 선생님 서비스라 문제없음). 프록시에서 버퍼링이 생기지 않는지 `curl -N`으로 확인해야 한다(참고노트 6장).
- `SseEmitter` 타임아웃은 20분(`app.ai-server.sse-timeout`)이다. 처음엔 5분으로 했지만, 자동 검토 재시도가 있으면 수업 준비 한 번이 5분을 넘어 연결이 끊기고 그래프 실행도 취소됐다(2026-10-19 실측: 루프 1회 약 2.5분 → 범주 병렬 생성 후 단축).
- 클라이언트가 끊기면 FastAPI 구독도 취소하고, 그러면 FastAPI 쪽 그래프 실행도 멈춘다. 다시 시작하면 새 thread로 처음부터 돈다.

## 재검토 조건
- 동시 스트림이 많아져 스레드가 부족할 때 → Java 21 가상 스레드(`spring.threads.virtual.enabled=true`)를 먼저 켜 보고, 그래도 부족하면 WebFlux를 다시 검토한다
