# ADR-0018: 진도 리포트는 Spring이 기록을 모아 보내고 ai-server가 계산한다 (저장하지 않음, 템플릿 문장)
- 상태: Accepted (2026-10-20)
- 관련 모듈: `backend/.../report/ReportController.java`, `record/LessonRecordRepository.java` (`findApprovedByStudent`), `aiclient/AiServerClient.java` (`progressReport`), `ai-server/app/standard/report.py`, `ai-server/app/api/report.py`, `frontend/src/pages/StudentReportPage.vue`
- 관련 ADR: [기획 ADR-0019](../planning-adr/0019-progress-report-for-retention.md), [ADR-0005](0005-data-access-ownership.md), [ADR-0013](0013-process-over-model.md), [ADR-0016](0016-standard-level-list-and-item-ids.md)

## 배경 (Context)
리포트에는 두 곳의 데이터가 필요하다. 수업 기록·약점은 Postgres(Spring만 접근), 표준 등급 목록·교재 대응표·교재 어휘는 ai-server 파일이다.
승인된 기록의 `approved` JSON에는 `strengths`, `errors`(post_lesson이 만든 `{student_said, correction, item_id, note}`)가 있고, 다룬 항목은 `lesson.covered_item_ids`에 있다.

## 결정 (Decision)
1. **경로**: 브라우저 → `GET /api/students/{id}/report?from&to` → Spring이 승인 기록 전체와 약점을 모아 → `POST /report/progress` (ai-server) → 결과를 그대로 돌려준다. [ADR-0005](0005-data-access-ownership.md) 방식 그대로다.
2. **기간 밖 기록도 보낸다.** "새로 배운 것"은 기간 전에 배운 것을 빼야 해서 누적이 필요하다. ai-server가 기간 전/안을 나눈다.
3. **계산 (ai-server, 순수 함수)**
   - 문법: 다룬 교재 항목 → `textbook_map` → `std-g-*` 항목.
   - 어휘: 다룬 교재 어휘의 글자·품사 → `word_level()`. 표현 칸(`(명사)를 좋아하다`)처럼 목록에 없으면 세지 않는다.
   - 반복 오류: 기간 안 오류를 `item_id`(없으면 바른 표현)로 묶어 2번 이상, 상위 3개.
   - 해결한 약점: `resolved_at`이 기간 안. 날짜가 없는 수업은 기록 승인일로 센다.
4. **문장은 템플릿**: `ko`, `ja`, `en` 템플릿을 코드에 두고 한국어 + 학생 모국어 두 개를 만든다. 학습 항목(문법·단어)과 선생님 기록은 한국어 그대로 넣는다. 등급별 비율은 문장에 넣지 않는다 (기획 결정 3, 테스트로 확인).
5. **저장하지 않는다.** 볼 때마다 계산한다. 기록 수십 개, 계산은 밀리초 단위다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| Spring에서 계산 | Java로 집계 | 왕복 하나가 준다 | 표준 등급 목록·대응표·교재 어휘가 ai-server에 있다. 옮기면 같은 데이터가 두 곳에 생긴다 |
| ai-server가 DB 직접 읽기 | 학생 id만 보냄 | 요청이 작다 | ADR-0005 위반 |
| 기간 안 기록만 보내기 | 요청이 작다 | 단순하다 | "새로 배운 것"과 "누적"을 구분할 수 없다 |
| LLM 문장 | 자연스러운 학생 언어 | 번역까지 된다 | 숫자를 틀릴 수 있다 (기획 ADR-0019 대안 A) |

## 결과 / 트레이드오프 (Consequences)
- 테스트: ai-server 리포트 8개 (기간 안·밖 구분, 새로 배운 것 vs 누적, 등급별 범위, 남은 문법, 반복 오류·약점, 비율이 문장에 없는지, 빈 기간, API). backend `RecordFlowTest`에 "승인 후 리포트가 기록·약점을 보내는지"를 더했다 (Docker가 없어 컴파일만 확인). 프론트 타입 검사 통과.
- 대가: 리포트를 열 때마다 학생의 승인 기록 전체를 보낸다. 학생 한 명에 수백 회가 되면 기간 전 기록은 "배운 항목 ID 목록"만 보내도록 줄인다.
- 대가: 교재 데이터(git 제외)가 없는 환경에서는 배운 항목을 셀 수 없다. 테스트는 그때 건너뛴다.

## 재검토 조건
- 수업 기록이 학생당 수백 회를 넘으면 → 기간 전 기록은 누적 항목 집합만 보낸다
- 월별 리포트를 보관하게 되면 (기획 ADR-0019 재검토) → `progress_report` 테이블을 둔다
