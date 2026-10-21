# ADR-0009: 그래프를 작업별로 나누고, HITL 위치를 그래프마다 다르게 둔다
- 상태: Accepted (2026-10-19)
- 관련 모듈: `ai-server/app/agent/lesson_prep/`, `ai-server/app/agent/intake.py`, `ai-server/app/agent/post_lesson/`, `backend/record/`

## 배경 (Context)
PRD 8-1은 그래프 네 개(router, student_intake, lesson_prep, post_lesson)를 제안했다. 구현해 보니 작업마다 "선생님 승인"의 모양이 다르다.
- 수업 준비: 범주별로 승인·직접 수정·피드백을 주고, 피드백한 범주만 **다시 생성**해야 한다 → 그래프가 사람 결정을 받아 이어서 돌아야 한다.
- 학생 등록·수업 후 기록: AI 초안을 보여 주고 **반영할지 말지**만 정한다 → 승인 뒤에 다시 생성할 일이 없다.

## 결정 (Decision)
| 작업 | 형태 | HITL 위치 | 상태 저장 |
|---|---|---|---|
| lesson_prep | LangGraph, `interrupt()` | 그래프 안 (human_review 노드) | SQLite checkpointer |
| post_lesson | LangGraph, 분기·루프만 (extract → gate → write_feedback ⇄ validate) | 그래프 밖: 초안을 "미처리 기록"으로 저장, 항목별 승인 시 Spring이 반영 | 없음 (결과는 Postgres `lesson_record.draft`) |
| student_intake | 그래프 없이 함수 두 개 (추출 + 검증) | 그래프 밖: 폼에 채워 보여 주고 선생님이 저장 | 없음 |
| router | Spring AI (ADR-0001) | – | – |

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 모든 작업을 interrupt 그래프로 | post_lesson도 승인에서 멈췄다가 재개 | HITL 방식이 하나로 통일 | 승인 뒤에 할 일이 "DB 반영"뿐이라 재개할 이유가 없다. checkpointer와 thread 관리만 늘어난다 |
| 큰 그래프 하나 + Supervisor | 라우터가 하위 그래프를 부름 (참고노트 2장 #6) | 진행 상황을 한 스트림으로 | 작업 사이에 수업이라는 실제 시간(며칠)이 끼어 있어 한 실행으로 묶이지 않는다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: post_lesson은 상태가 없어서 평가 스크립트(`ai-server/eval/run_eval.py`)가 노드 함수를 바로 불러 채점할 수 있다. 미처리 기록이 DB에 있어 대시보드 "할 일"로 바로 보인다.
- 대가: HITL 방식이 두 가지라 프론트 화면도 두 종류다 (범주별 결정 vs 항목별 체크).

## 재검토 조건
- 수업 후 기록에도 "이 항목만 다시 써 줘" 같은 피드백 재생성이 필요해지면 → interrupt 방식으로 옮긴다
