# ADR-0015: 수업 준비 그래프는 승인에서 끝나고, 7단계 틀은 briefing 노드가 코드로 붙인다
- 상태: Accepted (2026-10-20) — 그래프가 승인에서 끝난다는 결정은 유효. 7단계 틀을 briefing 노드가 붙인다는 부분은 [ADR-0034](0034-slide-plan-node.md)로 대체됨 (2026-10-21)
- 관련 모듈: `ai-server/app/agent/lesson_prep/graph.py`, `lesson_frame.py`, `nodes.py` (`plan_lesson`, `briefing`), `app/api/prep.py`
- 관련 ADR: [기획 ADR-0015](../planning-adr/0015-no-ppt-fixed-lesson-frame.md), [ADR-0013](0013-process-over-model.md), [ADR-0009](0009-graph-split-and-hitl-location.md)

## 배경 (Context)
기획에서 PPT를 빼고 고정된 7단계 수업 틀로 내놓기로 했다. 기술적으로 정할 것:
- 그래프의 끝 (`build_pptx → render_check` 루프를 어떻게 할지)
- 7단계 틀을 어디서 만들고 어디에 저장할지 (Spring의 `lesson` 테이블은 `plan`, `briefing`, `drafts`를 JSON Map으로 저장한다)
- 범주별 시간(`minutes`)과 틀의 단계별 시간을 어떻게 맞출지

## 결정 (Decision)
1. 그래프: `human_review -(모두 승인)-> END`. `build_pptx`, `render_check` 노드와 render 재시도 상태값을 뺀다.
2. 틀: `lesson_frame.py`에 단계(키, 이름, 50분 기준 시간, 할 일, 들어가는 범주)를 상수로 둔다.
   - `step_minutes()`: 수업 길이에 비례해 나누고, 반올림 오차는 활용 활동에 몰아 합계를 맞춘다.
   - `category_minutes()`: 범주 시간은 단계 시간에서 계산한다 (복습 = 복습 단계, 어휘 = 도입의 40%, 문법 = 도입 나머지 + 통제된 연습, 숙제 = 마무리).
   - `plan_lesson`은 이 함수로 범주 시간을 정한다. `code_checks`의 시간 합계는 "범주 시간 + 틀 전용 단계(워밍업·활용·피드백) = 수업 시간"으로 바꾼다.
3. 저장: `briefing` 노드가 `briefing.lesson_frame`(단계 목록)과 `briefing.references`(출처)를 붙인다. Spring은 `briefing`을 Map 그대로 저장하므로 **DB 마이그레이션이 필요 없다**. 검토 화면(interrupt payload)과 확정 결과(done) 모두에 들어간다.
4. 단계에는 범주 내용을 복사하지 않고 범주 키만 적는다. 화면이 `drafts`에서 꺼내 그린다. 선생님이 범주를 직접 수정해도 틀이 따로 낡지 않는다.
5. `done` 이벤트의 `pptx_file`, `pdf_file`은 항상 `null`로 보낸다. Spring·프론트의 기존 필드와 호환된다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 틀을 새 노드(`assemble_lesson`)로 | 승인 뒤 틀을 조립 | 역할이 분명 | 검토 화면에서는 틀을 볼 수 없다. 선생님은 승인 전에 전체 흐름을 봐야 한다 |
| `lesson` 테이블에 `frame` 칼럼 추가 | 별도 저장 | 스키마가 분명 | Flyway 마이그레이션, 엔티티·DTO 수정이 필요하다. 틀은 브리핑과 함께 읽히는 자료라 `briefing` 안에 두어도 충분하다 |
| 범주를 7단계로 다시 나누기 | 범주 = 단계 | 모델이 하나 | 범주별 HITL(승인·수정·피드백), 수업 후 기록, 평가셋이 모두 4범주 기준이다. 바꾸는 범위가 너무 크다 |
| PPT 코드 삭제 | 깔끔하다 | 죽은 코드가 없다 | 저장소가 git으로 관리되지 않아 되돌릴 수 없다. 모듈 테스트로 동작은 유지한다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 승인 직후 끝나서 빠르다. LibreOffice가 필요 없다.
- 대가: 범주 시간과 단계 시간이 1:1이 아니라 계산으로 이어진다 (어휘·문법이 도입 단계를 나눠 쓴다). 화면에는 단계 시간을 보여 준다.
- 대가: 브리핑 Map 안에 브리핑이 아닌 값(틀)이 섞인다.

## 재검토 조건
- 틀을 선생님이 직접 바꾸게 하려면 → 틀을 `lesson` 칼럼이나 선생님 설정으로 옮긴다
- 수준별 틀(기획 ADR-0015 재검토 조건)을 넣으면 → `STEPS`를 버전별 표로 바꾼다
