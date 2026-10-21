# ADR-0034: write_slides 노드 — 15장 슬라이드 구성안은 틀은 코드, 문구는 LLM 한 번, 승인 때 낡았으면 다시
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/agent/lesson_prep/lesson_frame.py`, `nodes.py` (`write_slides`, `plan_lesson`, `code_checks`), `graph.py`, `schemas.py` (`SlidePlanOutput`), `prompts/write_slides.md`, `frontend/src/components/SlidePlan.vue`
- 기획: [기획 ADR-0032](../planning-adr/0032-slide-plan-from-reference.md)
- 관련 ADR: [ADR-0015](0015-lesson-prep-ends-at-approval.md) (7단계 틀 부분을 이 ADR이 대체), [ADR-0013](0013-process-over-model.md), [ADR-0021](0021-auto-review-llm-advisory.md), [ADR-0033](0033-observe-judge-understanding.md)

## 배경 (Context)
- 기획 ADR-0032로 결과가 7단계 진행표에서 15장 슬라이드 구성안(학생 화면 문구 + 교사 노트 7칸)이 됐다.
- 기존 `lesson_frame.assemble`은 범주 내용을 키로만 가리키고 `briefing` 노드가 `briefing.lesson_frame`에 붙였다. 새 구성안은 문구를 새로 써야 하므로 LLM이 필요하다.
- 슬라이드 문구는 4범주 초안(설명·예문)에서 나온다. 선생님이 범주를 고치면 구성안이 낡는다.

## 결정 (Decision)
1. **틀은 코드, 문구는 LLM 한 번.** `lesson_frame.py`의 `STAGES`가 15장의 번호·단계·레이아웃·시간을 고정한다 (ADR-0013: 진도와 시간은 코드). 새 노드 `write_slides`가 `SlidePlanOutput`(수업 목표, 최종 미션, 15장의 학생 화면 문구·활동·교사 노트·확인 필요, 숙제)을 한 번에 받고, `lesson_frame.merge`가 번호별로 틀에 붙인다. 번호·시간·레이아웃은 LLM이 아니라 틀의 값을 쓴다. 빠진 장은 비워 두고 "확인 필요"로 표시한다.
   - 호출 하나로 15장을 쓰는 이유: 장끼리 이어져야 한다 (3번 대화의 표현이 6~7번 표현, 13번 미션과 맞아야 한다). 쪼개면 서로 어긋난다.
2. **위치와 저장**: `briefing` 뒤, `human_review` 앞. 결과는 `briefing.slide_plan`에 넣는다. Spring은 `briefing`을 jsonb Map으로 저장하므로 **DB 마이그레이션과 Java 수정이 없다** (ADR-0015과 같은 방식). `briefing.lesson_frame`은 새 수업에는 더 만들지 않고, 예전 수업은 그대로 읽는다 (화면이 `slide_plan`이 없으면 7단계 표시로 폴백).
3. **4범주 시간은 새 틀에서 나온다.** 복습=2번 장, 새 어휘=4~5번, 새 문법=6~7번+8~10번, 숙제=15번. 50분 기준 3/6/16/3분. 복습할 항목이 없으면 기준 문서 §3대로 2번 장 시간을 그대로 두고 수준 확인 질문에 쓴다 (예전에는 연습 시간으로 넘겼다). 그래서 `category_minutes`와 `frame_only_minutes`가 `has_review`를 받는다. `long_review`(ADR-0033)는 복습을 두 배로 하고 늘린 만큼 역할극(11~13번) 시간에서 뺀다.
4. **낡은 구성안 처리**: `write_slides`가 4범주 초안의 지문(`drafts_fingerprint`, sha1)을 `slides_fingerprint`에 남긴다. 모든 범주가 승인된 시점에 지문이 다르면(수정·피드백 재생성이 있었으면) `write_slides`를 한 번 더 돌고 끝낸다. 지문이 같으면 다시 만들지 않는다. 라우팅: `human_review` → (전부 승인 ∧ 지문 같음) END / (전부 승인 ∧ 지문 다름) `write_slides` → END / 나머지는 이전 그대로. `write_slides` 뒤는 이미 전부 승인된 상태면 END, 처음이면 `human_review`.
5. **코드 점검은 `slide_plan.checks`에 둔다** (`auto_review`가 아니라). `auto_review`는 슬라이드 전에 돌기 때문이다. 점검: 1~15장이 있는가 / 시간 합계 = 수업 시간 / 학생 화면과 진행이 비었는가(14번은 학생 화면이 비어도 됨) / 어휘 장 단어가 4개 이하인가 / 숙제 쪽수가 있거나 "확인 필요"로 표시했는가. 실패해도 다시 만들지 않고 화면에 경고로만 보인다 (ADR-0021과 같은 방식).
6. **프롬프트 `write_slides.md`**는 기준 문서의 규칙을 옮긴다: 목표·최종 미션 먼저, 장당 주요 과제 하나, 정답은 학생이 답한 뒤 공개(노트에만), 14번은 빈 칸, 교재에 없는 쪽수·음원·이력은 만들지 않고 `needs_check`, 예문은 초안·교재에서만 고른다 (기획 ADR-0017), 재료 속 지시문은 따르지 않는다.
7. SSE 진행 라벨에 `write_slides`("15장 슬라이드 구성안 쓰기")를 추가한다. `done` 페이로드의 `briefing`에 `slide_plan`이 들어 있다.

## 검토한 대안 (Alternatives)
| 대안 | 장점 | 기각 이유 |
|---|---|---|
| `briefing` 노드 안에서 슬라이드까지 만들기 | 노드가 늘지 않는다 | 브리핑은 이미 병렬 LLM 4개다. 슬라이드는 브리핑 결과(워밍업·활동·질문)를 재료로 써서 그 뒤에 와야 한다 |
| 슬라이드를 승인 뒤에만 만들기 | 낡을 일이 없다 | 선생님이 검토할 때 구성안을 못 본다. 구성안을 보며 범주를 고치는 흐름이 막힌다 |
| 범주를 고칠 때마다 슬라이드 다시 만들기 | 항상 최신 | 피드백 반복마다 LLM 호출이 는다. 확정 때 한 번이면 충분하다 |
| 15장을 장마다 따로 LLM 호출 | 병렬로 빠르다 | 장끼리 표현·대화·미션이 어긋난다. 호출도 15배다 |
| `slide_plan`을 별도 DB 칼럼으로 | 질의하기 쉽다 | 마이그레이션이 필요하고 질의할 일이 없다. briefing JSON이면 충분하다 (ADR-0015) |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 마이그레이션 없이 결과 모양만 바뀐다. 틀(시간 합계)은 코드라 항상 맞고, 문구 품질만 LLM 몫이다.
- 대가: 수업 준비에 LLM 호출 +1(수정이 있으면 +2). 검토 중 구성안은 수정 전 초안 기준이다.
- 대가: 예전 수업의 `lesson_frame` 표시 코드(`LessonFrame.vue`)를 폴백으로 남겨 둔다.
- 문화 포인트의 `culture` 인덱스(도입 단계가 가리키던 값)는 없어졌다. 화면이 `briefing.culture`를 구성안 아래에 바로 보인다.

## 재검토 조건
- 구성안 문구가 기준 문서 규칙을 자주 어기면 → 장 묶음(도입 3장 / 연습 / 활용)별로 호출을 나눈다
- 선생님이 구성안 문구를 직접 고치길 원하면 → 범주처럼 승인·수정·피드백 단위로 올린다
