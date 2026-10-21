# ADR-0033: 이해도는 LLM이 장면을 인용하고(observe) 코드가 판정한다(judge) — lesson.understanding에 저장해 복습 우선순위에 쓴다
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/agent/post_lesson/graph.py`, `ai-server/app/agent/post_lesson/schemas.py`, `ai-server/prompts/observe_understanding.md`, `ai-server/app/agent/lesson_prep/nodes.py`, `ai-server/app/agent/lesson_prep/lesson_frame.py`, `backend/.../lesson/Lesson.java`, `backend/.../lesson/StudentProfileAssembler.java`, `backend/.../record/RecordService.java`, `backend/src/main/resources/db/migration/V5__lesson_understanding.sql`, `frontend/src/pages/LessonRecordPage.vue`
- 관련 ADR: [기획 ADR-0029](../planning-adr/0029-understanding-from-transcript-drives-review.md), [ADR-0013](0013-process-over-model.md) (정형화 우선)

## 배경 (Context)
- 기획 ADR-0029: 녹취록에서 항목별 이해도를 정해 다음 수업 복습에 반영한다.
- 원칙(ADR-0013): 정답 규칙이 있는 판단은 코드, LLM은 작은 칸만. 로컬 8B 모델로도 돌아가야 한다.
- post_lesson 그래프는 `extract → gate → write_feedback ⇄ validate`이고, 승인은 Spring이 항목별로 반영한다.

## 결정 (Decision)
1. **post_lesson 그래프에 두 노드를 더한다**: `extract → gate → observe → judge → write_feedback ⇄ validate`
   - `observe` (LLM): gate가 확정한 다룬 항목(`covered_item_ids`)마다 학생 반응 장면을 찾는다. 장면 = `{item_id, kind, quote}`, kind는 `error | asked_again | hesitation | re_explained | self_corrected | correct`. quote는 녹취록 원문 그대로.
   - `judge` (코드): ① 다룬 항목이 아닌 ID, 녹취록에 없는 인용(공백·화자 표시를 무시하고 비교)은 버리고 경고를 남긴다. ② 항목별 점수 = error 2, asked_again 1, hesitation 1, re_explained 1, self_corrected 1, correct 0. 점수는 "얼마나 애먹었나"만 세고, 바로 맞힘은 깎지 않는다 (아래 대안 E). ③ 점수 ≥ 3 → `confused`, ≥ 1 → `shaky`, 그 밖에 `correct`가 하나라도 있으면 `ok`. 장면이 없는 항목은 결과에 넣지 않는다.
   - 결과는 `record_draft.understanding = [{item_id, level, score, episodes}]`.
2. **승인**: `ApproveRequest.understanding = {item_id: level}` (선생님이 바꾼 값). Spring이 ID 형식·level 값을 검사해 **`lesson.understanding` (jsonb, 기본 `{}`)** 에 저장한다 (V5 마이그레이션).
3. **수업 준비로 전달**: `StudentProfileAssembler`가 `lesson_history[].understanding`에 넣는다. ai-server `LessonRecord.understanding: dict[str, str] = {}`.
4. **복습 고르기** (`pick_review`): 직전 수업의 `confused` → `shaky` → 약점 → 직전 수업 문법 → 어휘, 최대 5개. 이유 문장에 개수를 적는다.
5. **복습 시간**: 복습 항목에 직전 수업 `confused`가 있으면 `step_minutes(..., long_review=True)`로 복습 단계를 두 배로 하고 늘린 만큼 활용 활동에서 뺀다. `assemble`과 코드 점검(시간 합계)도 같은 판단(`nodes.long_review`)을 쓴다.
6. 녹취록 상한 30,000자: `PostLessonRequest.raw_note`, `RecordRequest.rawNote`, 프론트 `NOTE_MAX`.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| A. extract 스키마에 장면 칸 추가 | LLM 호출 한 번 | 호출 수 그대로 | 이미 칸이 많은 출력이 더 커져 작은 모델이 흔들린다. gate가 확정한 다룬 항목을 기준으로 볼 수 없다 |
| B. LLM이 level까지 정함 | observe가 판정까지 | 코드 없음 | 기준이 프롬프트에 묻혀 조절·평가가 어렵다 (기획 ADR-0029 대안 B) |
| C. 이해도를 lesson_record.approved에서 읽기 | 저장 칼럼 없음 | 마이그레이션 없음 | 수업 준비 때마다 기록 JSON을 뒤져야 한다. covered_item_ids처럼 lesson에 두는 편이 일관적이다 |
| E. 바로 맞힘을 −1로 상쇄 (처음 구현) | 맞힌 만큼 점수를 깎음 | 수업 안에서 익힌 항목을 걸러 냄 | 샘플 녹취록(`transcript_sample_ja.txt`)에서 을/를을 세 번 틀리고 "계속 틀려요"라고 했는데 맞힘 4개에 상쇄돼 "조금 헷갈림"이 나왔다. 복습 우선순위에는 애먹은 정도가 중요하다. 스스로 고침도 0 → 1로 올렸다 (아직 자동으로 안 나옴) |
| D. observe를 write_feedback과 병렬 | 대기 시간 줄임 | 빠름 | validate 재작성 루프와 합류가 복잡해진다. 먼저 순차로 두고 느리면 바꾼다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 판정 기준이 코드 숫자라 테스트·조정이 쉽다. 인용 검사로 지어낸 근거를 막는다.
- 좋은 점: 승인된 이해도가 lesson에 남아 진도 리포트·진도 조정에서 다시 쓸 수 있다.
- 대가: LLM 호출 1회 추가(quality 티어). 녹취록 전체를 한 번 더 읽는다.
- 대가: 같은 과를 이어서 하는 수업이면 그 과의 항목은 복습 후보(`past_items`)에서 빠진다 (새 내용으로 다시 다루므로 의도대로다).

## 재검토 조건
- 점수 기준이 선생님 판단과 자주 다르면 숫자를 조정한다
- 녹취록이 길어 observe가 느리면 대안 D(병렬) 또는 항목 주변만 잘라 보내기를 검토한다
