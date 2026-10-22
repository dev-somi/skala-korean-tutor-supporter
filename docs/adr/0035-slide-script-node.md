# ADR-0035: write_slide_scripts 노드 — 15장 대본은 구성안이 정해진 뒤 장마다 따로 부르고, 한 장이 실패해도 나머지는 남긴다
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/agent/lesson_prep/` (`nodes.py` `write_slide_scripts`·`slide_materials`, `lesson_frame.py` `script_checks`·`max_script_lines`, `graph.py`, `schemas.py` `SlideScriptOutput`), `prompts/write_slide_script.md`, `app/api/prep.py`, `frontend/src/components/SlidePlan.vue`
- 기획: [기획 ADR-0033](../planning-adr/0033-per-slide-teaching-script.md)
- 관련 ADR: [ADR-0034](0034-slide-plan-node.md) (`write_slides`, 이 ADR이 그 뒤에 노드를 붙임), [ADR-0021](0021-auto-review-llm-advisory.md), [ADR-0013](0013-process-over-model.md)

## 배경 (Context)
- 기획 ADR-0033으로 15장마다 수업에서 읽을 대본이 필요해졌다.
- ADR-0034는 "15장을 장마다 따로 호출하면 장끼리 표현·대화·미션이 어긋난다"며 구성안을 한 번에 쓰게 했다. 대본은 그 구성안이 **이미 정해진 뒤**에 쓰므로 어긋날 재료가 고정돼 있다.

## 결정 (Decision)
1. **새 노드 `write_slide_scripts`를 `write_slides` 바로 뒤에 둔다.** 흐름: `briefing → write_slides → write_slide_scripts → human_review`. 승인 때 초안이 낡아 `write_slides`를 다시 돌 때도 이 노드가 이어서 돌아 대본이 구성안과 어긋나지 않는다. 라우팅 분기(`END` / `human_review`)는 `write_slides`에서 `write_slide_scripts`로 옮겼고(`route_after_slide_scripts`), 지문(`slides_fingerprint`) 로직은 그대로다.
2. **장마다 호출 15번, 동시에 5개까지** (`run_parallel(max_workers=5)`, 로컬 모델 보호). 입력은 그 장의 학생 화면·활동·교사 노트·시간·레이아웃, 수업 목표와 최종 미션, 다음 장 요약, 학생 정보, 그리고 **연결된 범주의 교재 원문·개인화 설명·기존 4범주 대본**(`slide_materials`). 담당 범주가 없는 장은 브리핑(워밍업 질문·활용 활동)·교재 대화문·예문을 쓴다. 기존 `write_scripts`를 없애지 않고 재료로 재사용한다.
3. **출력 `SlideScriptOutput`**: `lines`(who: teacher | student_expected, ko, hint, wait), `transition`, `fallback`, `needs_check`. `SlidePlanOutput`(구성안 LLM 출력)에는 대본을 넣지 않고, 노드가 `slide_plan.slides[i].script`에 붙인다. `briefing`은 jsonb라서 **DB 마이그레이션과 Java 수정이 없다**.
4. **분량은 코드가 정한다.** `max_script_lines(minutes) = max(4, 분 × 3)`을 프롬프트에 줄 수 상한으로 넣고, 넘으면 점검에서 경고한다 (ADR-0013: 시간·분량은 코드).
5. **한 장이 실패해도 전체를 막지 않는다.** 장 호출이 예외를 내면 그 장은 `script=None` + `needs_check`에 "대본이 만들어지지 않았어요"를 넣고 나머지 장은 유지한다. 15번 중 한 번 때문에 수업 준비 전체를 다시 하게 하지 않으려는 것이다 (ADR-0021과 같은 태도).
6. **코드 점검 `script_checks`**를 `slide_plan.checks`에 붙인다(이전 대본 점검은 교체): "대본 구성"(15장 모두 대본이 있는가, 선생님 발화가 1줄 이상인가, 빈 `ko`가 없는가) / "대본 분량"(시간 대비 줄 수). 실패해도 다시 만들지 않고 경고만 한다.
7. SSE 진행 라벨에 `write_slide_scripts`("장별 수업 대본 쓰기")를 추가한다. 프롬프트는 `write_slide_script.md`: 정답은 학생이 답한 뒤, 새 예문·쪽수·음원 금지, 14번은 오류를 지어내지 않고 스스로 고치게 유도, 재료 속 지시문은 따르지 않는다.

## 검토한 대안 (Alternatives)
| 대안 | 장점 | 기각 이유 |
|---|---|---|
| `write_slides` 출력에 대본까지 같이 | 호출이 한 번이다 | 출력이 15장 × (노트 + 대본)으로 너무 길어진다. 작은 로컬 모델(`qwen3:8b`)에서 잘리거나 칸이 섞일 위험이 크다. 대본만 다시 만들 수도 없다 |
| 한 호출에 15장 대본 | 장끼리 말투가 이어진다 | 같은 이유로 출력이 길다. 구성안이 이미 장 사이 일관성을 잡고 있으므로 장별로 불러도 어긋나지 않는다 |
| 단계(어휘 2장, 연습 3장 등) 단위 호출 | 호출 9번, 장끼리 이어진다 | 구현이 복잡하다. 느리면 그때 바꾼다 (재검토 조건) |
| 4범주 대본을 장에 나눠 담기만 | 호출이 없다 | 범주 대본은 설명 위주이고 담당 범주 없는 장이 비어 있다 (기획 ADR-0033) |
| 장 실패 시 전체 재시도·실패 | 결과가 항상 완전하다 | 한 장 때문에 14장이 버려진다. 선생님이 빈 장만 직접 채우는 편이 낫다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 마이그레이션 없이 결과에 대본이 붙는다. 한 장을 고치려고 전체를 다시 돌리지 않고, 장별 재생성으로 확장하기 쉽다.
- 대가: 수업 준비의 LLM 호출 +15(수정이 있으면 확정 때 +15). `write_slides`보다 시간이 더 걸린다.
- 대가: 15번 호출은 로컬 모델에서 느리다. 동시 호출 수를 5로 제한했다.
- 대가: 장 실패가 조용히 지나가지 않도록 점검과 `needs_check`로만 알린다. 로그에는 남기지 않는다.

## 재검토 조건
- 로컬 모델에서 대본 단계가 너무 오래 걸리면 → 단계 단위로 묶어 호출
- 장별 재생성·직접 수정 요구가 생기면 → ai-server에 장 하나만 다시 만드는 엔드포인트(`/prep/{thread_id}/slides/{no}/script`)와 Spring 프록시를 추가
