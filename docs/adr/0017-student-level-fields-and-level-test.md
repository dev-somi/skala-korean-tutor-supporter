# ADR-0017: 학생 수준 칸은 DB에서 nullable·API에서 필수로 두고, 레벨테스트 문항과 판정은 ai-server가 가진다
- 상태: Accepted (2026-10-20), 결정 7의 "저장하지 않는다"와 결정 8만 Superseded by [ADR-0019](0019-level-test-student-screen-and-results.md) (2026-10-20)
- 관련 모듈: `backend/.../db/migration/V2__student_level_persona.sql`, `student/*`, `leveltest/LevelTestController.java`, `aiclient/AiServerClient.java`, `ai-server/app/standard/level_test.py`, `ai-server/app/api/level_test.py`, `ai-server/data/standard/level_test.json`, `frontend/src/pages/LevelTestPage.vue`, `components/StudentForm.vue`, `shared/constraints.json`
- 관련 ADR: [기획 ADR-0018](../planning-adr/0018-level-from-trial-test-persona-by-teacher.md), [ADR-0016](0016-standard-level-list-and-item-ids.md), [ADR-0005](0005-data-access-ownership.md), [ADR-0013](0013-process-over-model.md)

## 배경 (Context)
기획에서 현재 수준(표준 등급 0~6)을 필수로, 목표 수준·학습 목적을 선택 칸으로 넣고, 체험수업 레벨테스트를 제공하기로 했다. 정할 것:
- 이미 있는 학생 행에 필수 칸을 어떻게 더할지
- 레벨테스트 문항과 판정 규칙을 어디에 둘지 (프론트에는 단위 테스트 도구가 없다. 타입 검사만 있다)

## 결정 (Decision)
1. **칸**: `student`에 `standard_level`(0~6), `target_level`(1~6), `level_assessed_on`(date), `persona`(4개 값)를 더한다. 값 범위는 DB check 제약과 Bean Validation 양쪽에서 막는다. 기존 `level`은 세부 메모로 뜻만 바꾸고 이름은 그대로 둔다 (Spring·ai-server·채팅 도구·프론트가 모두 쓰는 이름이라 바꾸는 비용이 크다).
2. **필수는 API에서**: DB 칸은 nullable, `StudentRequest.standardLevel`은 `@NotNull`. 기존 학생에게 등급을 지어 넣지 않기 위해서다. 기존 학생은 다음에 고칠 때 등급을 골라야 저장된다. 화면은 null을 "수준 미정"으로 주황색 표시한다.
3. **ai-server로 넘기기**: `StudentProfileAssembler`가 `standard_level`, `target_level`, `persona`를 프로필에 담는다. ai-server `StudentProfile`에 같은 칸을 선택 값으로 더한다. 수업 준비는 아직 이 값을 쓰지 않는다 (예문 거르기 연결 때 쓴다).
4. **자연어 등록 권위 게이트**: 범위 밖 등급과 모르는 학습 목적은 지우고 경고한다. 현재 수준이 비면 "레벨테스트 결과로 골라 주세요" 경고를 항상 붙인다. 프롬프트에는 "등급은 메모에 분명할 때만, 학습 목적은 추천"이라고 적는다.
5. **레벨테스트 문항은 ai-server 데이터**: `data/standard/level_test.json`에 표준 항목 ID와 질문만 적고, 글자·길잡이말·등급은 로드할 때 등급 목록에서 채운다. 로드할 때 ID가 있는지, 문항 등급과 표준 항목 등급이 같은지 검사한다. 문항 ID(`hangul-1`, `L2-g3`, `L2-v1`)는 코드가 붙인다.
6. **판정도 ai-server**: `score(answers)`는 순수 함수이고 pytest로 규칙을 고정한다. 화면은 맞음/틀림이 바뀔 때마다 `POST /level-test/score`를 부른다 (늦게 온 응답은 버린다). 없는 문항 ID는 422.
7. **경로**: 브라우저 → `GET /api/level-test`, `POST /api/level-test/score` (Spring, 그대로 전달) → ai-server ([ADR-0001](0001-service-role-split.md)). 저장하지 않으므로 DB를 거치지 않는다.
8. **등록으로 넘기기**: [이 결과로 학생 등록]은 `/students/new?level=2&assessedOn=YYYY-MM-DD&note=…`로 간다. 등록 화면은 쿼리 값을 먼저 채우고, 그 뒤 AI 초안을 받아도 레벨테스트 등급과 날짜를 덮어쓰지 않는다.
9. 학습 목적 → 중심 교재 표, 등급 이름은 `shared/constraints.json`에 두고 프론트·ai-server·Spring 상수에 같은 값을 적는다 (기존 방식).

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| DB `not null default 1` | 기존 학생을 1급으로 채움 | 스키마가 엄격하다 | 레벨테스트를 안 한 학생에게 등급을 지어낸다. 기획 ADR-0018의 "짐작하지 않는다"와 어긋난다 |
| `level` 칸 이름 바꾸기 (`level_note`) | 뜻에 맞는 이름 | 읽기 쉽다 | 세 서비스·채팅 도구·평가셋까지 바꿔야 한다. 주석과 화면 이름으로 충분하다 |
| 판정을 프론트에서 | TS 함수 | 요청이 없다 | 프론트에 단위 테스트가 없다. 규칙이 바뀌면 검증할 곳이 없다 |
| 문항을 프론트 정적 파일로 | Vue가 JSON import | 서버 왕복 없음 | 문항이 표준 ID와 등급을 참조하는데 등급 목록은 ai-server에 있다. 검사를 한 곳에서 못 한다 |
| LLM이 문항 생성 | 학생마다 다른 문항 | 다양하다 | 매번 다른 테스트는 결과를 비교할 수 없다. 정답이 있는 일은 고정한다 (ADR-0013) |
| 레벨테스트 결과를 DB에 저장 | 문항별 기록 | 나중에 분석 | 이번 범위에서는 등급과 날짜만 있으면 된다. 학생 엔티티 밖 새 테이블이 필요하다 |

## 결과 / 트레이드오프 (Consequences)
- 테스트: ai-server 전체 64개 통과. 이번에 더한 것은 레벨테스트 10개(데이터 무결성, 문항이 그 등급 안의 단어만 쓰는지, 판정 규칙, API)와 등록 게이트 2개다. 프론트 `vue-tsc` 통과. backend는 컴파일만 확인했다 (Testcontainers 테스트는 Docker가 필요하다).
- 대가: 기존 학생은 수정 화면을 열면 등급을 고를 때까지 저장할 수 없다.
- 대가: 맞음/틀림을 누를 때마다 요청이 간다. 문항이 60개 남짓이라 부담은 작다.
- 대가: 레벨테스트 문항별 결과는 남지 않는다. 등급·날짜·관찰 메모만 학생 카드에 남는다.

## 재검토 조건
- 레벨테스트 결과를 다시 보거나 비교할 일이 생기면 → `level_test_result` 테이블을 둔다
- 프론트에 단위 테스트 도구를 들이면 → 판정을 프론트로 옮겨 요청을 없앨 수 있다
- 문항을 선생님이 고치고 싶어 하면 → 문항 편집 화면과 저장소를 둔다 (지금은 JSON 파일)
