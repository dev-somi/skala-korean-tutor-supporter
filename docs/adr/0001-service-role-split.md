# ADR-0001: Spring AI 백엔드와 FastAPI AI 서버의 역할 분담
- 상태: Accepted (2026-10-19)
- 관련 모듈: `backend/`, `ai-server/`

## 배경 (Context)
PRD는 FastAPI 단일 백엔드를 전제로 썼지만, 스택을 Vue + Spring AI + FastAPI 3계층으로 바꿨다.
LLM을 부르는 곳이 Spring과 FastAPI 두 군데가 되면서 어느 쪽이 무엇을 맡을지 정해야 한다.
수업 준비 그래프(`korean-ppt-ai-agent`, LangGraph, 약 1,200줄 + pytest)는 이미 Python으로 동작한다. 마감은 4일 뒤(10/22)다.

## 결정 (Decision)
- **Spring Boot + Spring AI**: 프론트가 부르는 유일한 API, DB 읽기·쓰기, HITL 승인 반영, 시간 측정(TimeLog), 채팅 라우팅 게이트와 조회 답변(Haiku, Tool Calling).
- **FastAPI**: LangGraph 그래프(`student_intake`, `lesson_prep`, `post_lesson`)와 PPT/PDF 생성. 그래프 상태는 LangGraph checkpointer로 관리한다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| Spring AI가 LLM 전부 | 모든 그래프를 Java로 다시 작성하고 FastAPI는 PPT 렌더링만 | Java 한 언어로 AI 로직 통일 | 동작하는 LangGraph 코드(루프, interrupt, checkpointer)를 4일 안에 다시 만들기 어렵다 |
| Spring은 게이트웨이만 | Spring은 CRUD와 프록시만, 라우터 포함 AI는 전부 FastAPI | 경계가 가장 단순 | Spring AI를 거의 쓰지 않아 스택을 고른 의미가 없다. 조회 질문도 FastAPI를 한 번 더 거친다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 기존 Python 그래프와 테스트를 그대로 다시 쓴다. 단순 조회는 Spring 안에서 끝나서 빠르고 싸다(참고노트 2장 #7 라우팅 게이트).
- 대가: LLM 설정(모델명, API 키)이 두 곳에 생긴다 → 같은 `.env` 키 이름을 쓴다. 서비스 간 스키마(요청·SSE 이벤트)를 맞춰야 한다 → `shared/constraints.json`과 문서화된 이벤트 스키마.

## 재검토 조건
- 그래프를 Java로 옮길 이유가 생길 때 (예: Spring AI에 LangGraph 수준의 상태 그래프·interrupt 지원이 생김)
- FastAPI 장애·지연이 잦아 서비스 하나로 합치는 편이 나을 때
