# ADR-0019: 학생 화면은 같은 브라우저의 별도 창(BroadcastChannel), 레벨테스트 결과는 `level_test_result`에 저장하고 apply로 학생에 반영한다
- 상태: Accepted (2026-10-20)
- 관련 모듈: `frontend/src/levelTestScreen.ts`, `pages/LevelTestPage.vue`, `pages/LevelTestScreenPage.vue`, `pages/LevelTestResultPage.vue`, `components/LevelTestResultCard.vue`, `pages/StudentNewPage.vue`, `App.vue`, `router.ts`, `backend/.../V4__level_test_result.sql`, `leveltest/*`, `dashboard/DashboardController.java`
- 관련 ADR: [기획 ADR-0021](../planning-adr/0021-student-screen-level-test-saved-result.md), [ADR-0017](0017-student-level-fields-and-level-test.md) (결정 7·8을 이 ADR이 바꾼다), [ADR-0005](0005-data-access-ownership.md), [ADR-0001](0001-service-role-split.md)

## 배경 (Context)
기획에서 레벨테스트에 화면 공유용 학생 화면을 두고, 결과를 저장한 뒤 선생님이 확인하면 학생 카드에 반영하기로 했다. 정할 것:
- 선생님 화면과 학생 화면을 어떻게 맞출지 (서비스는 로컬에서만 돈다, [ADR-0008](0008-local-dev-runtime.md))
- 결과를 어디에, 어떤 모양으로 저장하고 언제 학생에 쓸지

## 결정 (Decision)
1. **동기화는 BroadcastChannel**: 학생 화면(`/level-test/screen`)은 선생님이 같은 브라우저에서 여는 창이다. 선생님 화면이 `level-test-screen` 채널로 `{type:'show', lang, item}` 또는 `{type:'done'}`을 보낸다. 학생 창은 열리면 `hello`를 보내고, 선생님 화면은 지금 상태를 다시 보낸다(새로고침 대비). 서버는 거치지 않는다.
2. **학생 화면에는 보낼 것만 보낸다**: `item`은 `{kind, text, level, index, total}`뿐이다. 예시 답·확인할 점·표준 ID·채점 결과는 메시지에 담지 않으므로 학생 화면 코드가 실수로 보여 줄 수 없다.
3. **학생 화면은 메뉴 없는 레이아웃**: 라우트 `meta.bare`면 `App.vue`가 헤더·채팅·토스트 없이 `RouterView`만 그린다.
4. **결과 테이블** `level_test_result`(V4): `answers`(jsonb, 문항 ID → bool), `score`(jsonb, ai-server 판정 그대로), `suggested_level`, `note`, `status`(pending | applied | dismissed), `student_id`(nullable, 학생 삭제 시 null), `applied_level`, `taken_at`, `decided_at`.
5. **판정은 저장할 때 서버가 다시 한다**: `POST /api/level-test/results {answers, note}` → Spring이 ai-server `/level-test/score`를 불러 결과를 함께 저장한다. 화면이 보낸 추천 등급은 믿지 않는다. 빈 답은 400.
6. **반영은 별도 API**: `POST /api/level-test/results/{id}/apply {studentId, level?}`가 같은 트랜잭션에서 학생의 `standard_level`·`level_assessed_on`(테스트 날짜)을 바꾸고 결과를 applied로 바꾼다. `level`이 없으면 추천 등급. 세부 메모(`level`)는 비어 있을 때만 관찰 메모로 채운다. pending이 아니면 409. `dismiss`도 같은 규칙.
7. **새 학생 등록**: 결과 카드가 `/students/new?result=7&level=…&assessedOn=…&note=…`로 보낸다. 등록 화면은 학생을 만든 다음 `apply(result, 새 학생 id, 폼에서 고른 등급)`을 부른다. 학생 생성과 반영이 두 요청이라, 두 번째가 실패하면 학생은 생기고 결과는 대기로 남는다(대시보드에서 다시 반영하면 된다).
8. **할 일**: `GET /api/dashboard/todos`에 `pendingLevelTests`를 더한다. 결과 카드는 `/level-test/results/:id`에서도 연다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| 서버 상태 + 폴링/SSE | 지금 문항을 DB나 메모리에 두고 학생 화면이 받아 감 | 다른 기기에서도 열 수 있다 | 화면 공유라 같은 브라우저면 충분하다. 테스트 세션 상태를 서버에 둘 이유가 없다 |
| `localStorage` + `storage` 이벤트 | 같은 브라우저 창끼리 공유 | 오래된 브라우저도 된다 | 지난 테스트 값이 남는다. 지울 시점을 따로 관리해야 한다 |
| 한 창에서 선생님 영역/학생 영역 나누기 | 창 하나 | 창 관리가 없다 | 화면 공유에서 일부 영역만 공유하기 어렵다 |
| 학생 엔티티에 결과 칸만 추가 | 테이블 없이 | 단순하다 | 학생이 없을 때(체험수업 직후) 둘 곳이 없다. 추천과 최종 등급 비교도 못 한다 |
| 결과 저장과 학생 생성을 한 API로 | `POST /students`에 `levelTestResultId` | 원자적이다 | 학생 API가 레벨테스트를 알게 된다. 실패해도 대기로 남아 다시 할 수 있어 두 요청으로 충분하다 |

## 결과 / 트레이드오프 (Consequences)
- 테스트: backend `LevelTestResultFlowTest` 4개(저장 → 할 일 → 반영, 등급 바꿔 반영과 메모 유지, 버리기, 빈 답 거절). 전체 18개 통과. 프론트 `vue-tsc` 통과. BroadcastChannel 동기화는 자동 테스트가 없고 브라우저에서 확인한다.
- 대가: 학생 창은 같은 브라우저(같은 출처)에서 열어야 한다.
- 대가: [ADR-0017](0017-student-level-fields-and-level-test.md) 결정 7의 "저장하지 않으므로 DB를 거치지 않는다"와 대안 표의 "결과를 DB에 저장" 기각을 이 ADR이 뒤집는다. 채점 중(`/score`)은 여전히 저장하지 않는다.

## 재검토 조건
- 학생이 다른 기기에서 직접 들어와야 하면 → 서버 상태와 학생용 링크(토큰)를 둔다
- 선생님이 결과 목록을 다시 보고 싶어 하면 → 학생 화면에 레벨테스트 이력을 붙인다 (데이터는 이미 있다)
