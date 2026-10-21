# ADR-0005: DB는 Spring만 다루고, FastAPI는 요청으로 데이터를 받는다
- 상태: Accepted (2026-10-19)
- 관련 모듈: `backend/aiclient`, `ai-server/` API

## 배경 (Context)
그래프에는 학생 프로필, 약점, 지난 수업 기록이 필요하다. PRD 8-3의 원칙은 **"AI는 DB에 직접 쓰지 않는다. 모든 쓰기는 선생님 승인을 거친다."**
FastAPI가 데이터를 어떻게 얻을지에 따라 이 원칙을 지키기 쉬운지가 달라진다.

## 결정 (Decision)
- DB를 읽고 쓰는 것은 **Spring만** 한다.
- 그래프를 시작할 때 Spring이 필요한 데이터(프로필, 현재 약점, 최근 기록, 수업 구성안)를 JSON으로 조립해 요청 본문에 담는다.
- FastAPI는 **초안만** 돌려준다. 선생님이 승인하면 Spring이 반영한다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| FastAPI가 DB를 직접 읽기 | FastAPI가 Postgres를 읽기 전용으로 조회 | 요청이 단순해지고 필요한 만큼만 읽는다 | 스키마를 Java(JPA)와 Python 두 곳에서 관리해야 하고, 쓰기 권한이 섞일 여지가 생긴다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: HITL 원칙이 프롬프트나 약속이 아니라 **구조로** 보장된다(FastAPI에는 DB 접속 정보가 없다). FastAPI 테스트는 JSON만 넣으면 돼서 쉽다.
- 대가: 요청 본문이 커진다. Spring이 "그래프에 무엇이 필요한지" 알아야 한다 → 요청 스키마를 ai-server의 Pydantic 모델로 정의하고 문서화한다.
- 권위 게이트(교재 ID 존재 검사)는 교재 파일을 가진 FastAPI에서, 약점 변경이 현재 약점과 맞는지는 Spring이 보낸 목록으로 FastAPI에서 검사하고, 반영 직전에 Spring이 한 번 더 확인한다.

## 재검토 조건
- 요청 payload가 너무 커지거나(예: 수업 이력 전체가 필요해짐) 그래프가 실행 중에 추가 데이터를 조회해야 할 때 → Spring에 조회 API를 열고 FastAPI가 Tool로 부른다
