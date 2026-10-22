# ADR-0042: 주 메뉴에 AI 채팅 탭을 두고, 플로팅 위젯과 한 스토어로 같은 대화를 쓴다
- 상태: Accepted (2026-10-22)
- 관련 모듈: `frontend/src/App.vue`, `router.ts`, `pages/ChatPage.vue`, `components/{ChatWidget,ChatMessageList,ChatComposer}.vue`, `stores/chat.ts`
- 관련 ADR: [ADR-0029](0029-nav-student-prep-tabs.md)·[ADR-0038](0038-nav-standard-tab.md) (주 메뉴 구성. 이 ADR은 메뉴에 한 칸을 더한다), [ADR-0041](0041-chat-history-in-postgres.md), [기획 ADR-0035](../planning-adr/0035-chat-tab-history-and-language-toggle.md)

## 배경 (Context)
기획 ADR-0035로 큰 화면 채팅 탭이 생기고, 플로팅 위젯과 같은 대화를 써야 한다.

## 결정 (Decision)
- 주 메뉴: **대시보드 · 학생 · 수업 준비 · 어휘·문법 · AI 채팅**. 라우트는 `/chat/:id?` (id가 없으면 지금 대화).
- 메시지 목록(`ChatMessageList`)과 입력창+언어 토글(`ChatComposer`)을 위젯에서 떼어 내 위젯·탭이 같이 쓴다. 상태는 Pinia `chat` 스토어 하나.
- 마지막 대화 id와 언어 토글은 localStorage에 둔다. 위젯을 처음 열거나 탭에 들어가면 그 대화 기록을 서버에서 한 번 불러온다.
- 위젯의 [넓게 보기]는 [AI 채팅 탭에서 크게 보기]로 바꾼다. `/chat`에서는 플로팅 버튼을 숨긴다.
- 좁은 화면에서는 대화 목록을 버튼으로 덮어 연다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| A. 더보기에 넣음 | 주 메뉴 유지 | 메뉴가 짧다 | 수업 중 자주 쓰는 화면이라 한 번에 가야 한다 |
| B. 탭 페이지를 위젯과 따로 구현 | 코드 독립 | 서로 안 깨진다 | 근거 카드·버튼·다시 보내기를 두 번 만들고 고쳐야 한다 |

## 결과 / 트레이드오프 (Consequences)
- 주 메뉴가 5개라 좁은 화면에서 가로로 밀 때가 늘어난다.
- 위젯의 [넓게 보기] 모드는 없어졌다.

## 재검토 조건
- 메뉴가 더 늘면 → 주 메뉴 구성을 다시 본다
