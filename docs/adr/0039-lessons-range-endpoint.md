# ADR-0039: 대시보드 달력은 기간별 수업 목록 API(`GET /api/lessons?from&to`) 하나로 받고, 상태는 프론트가 정한다
- 상태: Accepted (2026-10-22)
- 관련 모듈: `backend/.../lesson/LessonController.java`, `LessonRepository.findInRange`, `frontend/src/pages/DashboardPage.vue`
- 관련 ADR: [기획 ADR-0034](../planning-adr/0034-dashboard-calendar.md)

## 배경 (Context)
- 대시보드를 월간 달력으로 바꾼다(기획 ADR-0034). 보이는 6주 동안의 모든 학생 수업이 필요하다.
- 지금은 전체 수업 목록 API가 없어서 [수업 준비] 탭이 학생마다 `/students/{id}/lessons`를 부른다.
- 기존 `/api/dashboard/todos`는 할 일 목록 모양이라 날짜별 달력에는 맞지 않는다.

## 결정 (Decision)
- `GET /api/lessons?from=YYYY-MM-DD&to=YYYY-MM-DD`를 추가한다. 응답은 기존 `LessonView` 목록.
  - 기간 안의 수업 전부 + 날짜 미정(`lessonDate` null)이면서 수업 전(planned/prepared)인 수업.
  - 쉬는(paused) 학생의 수업은 뺀다. `join fetch student`로 한 번에 읽는다.
- 달력 상태(준비 전/준비 중/준비 완료/기록 필요/기록 확인 대기/끝)는 프론트가 `status`, `prepThreadId`, `lessonDate`, 오늘 날짜로 계산한다. 오늘 날짜는 브라우저의 로컬 날짜를 쓴다.
- 달력 라이브러리는 넣지 않고 Tailwind 7열 격자로 그린다.
- `/api/dashboard/todos`는 남긴다 (테스트와 다른 호출이 쓴다).

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| A. 학생별 목록을 프론트에서 모음 | PrepPage 방식 | API 추가 없음 | 학생 수만큼 요청, 기간과 상관없이 전부 받는다 |
| B. 서버가 상태까지 계산한 달력 전용 DTO | `/dashboard/calendar` | 프론트가 단순 | "오늘"이 서버·브라우저 시간대에 따라 달라지고, 상태 표시 규칙이 화면 일이다 |
| C. 달력 라이브러리(FullCalendar 등) | 기능 많음 | 주간·드래그 등 | 의존성 추가, 월간 칸 표시만 필요 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 달마다 요청 한 번. 같은 API를 나중에 [수업 준비] 탭에도 쓸 수 있다.
- 대가: 상태 규칙이 프론트에 있어서 채팅 등 다른 곳에서 같은 상태를 말하려면 규칙을 다시 옮겨야 한다.

## 재검토 조건
- 채팅에서 "이번 주 준비 안 된 수업" 같은 질문을 받게 되면 → 상태 계산을 백엔드로 옮긴다
