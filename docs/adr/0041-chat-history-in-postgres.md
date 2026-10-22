# ADR-0041: 채팅 기록을 Postgres에 저장하고, LLM 문맥(ChatMemory)도 같은 표에서 읽는다
- 상태: Accepted (2026-10-22)
- 관련 모듈: `backend/chat/{ChatService,ChatHistoryService,ChatHistoryController,DbChatMemory}.java`, `config/ChatClientConfig.java`, `db/migration/V7__chat_history.sql`
- 관련 ADR: [기획 ADR-0035](../planning-adr/0035-chat-tab-history-and-language-toggle.md), [ADR-0042](0042-nav-chat-tab-shared-conversation.md)

## 배경 (Context)
- 대화는 프론트 Pinia와 Spring `MessageWindowChatMemory`(JVM 메모리, 최근 20개)에만 있었다. 새로고침이나 backend 재시작이면 사라졌다.
- 기획 ADR-0035로 대화 목록과 기록 다시 보기가 필요해졌다. 답에 붙는 문법 근거 카드·이동 버튼도 다시 그려야 한다.

## 결정 (Decision)
- 표 두 개: `chat_conversation(id, title, created_at, updated_at)`, `chat_message(conversation_id, role, text, meta jsonb)`. 대화 id는 프론트가 만든 `conversationId`를 그대로 쓴다.
- 답의 `meta`에 `intent`, `studentName`, `lang`, `sources`, `actions`, `error`를 SSE로 보낸 모양 그대로 넣는다.
- `ChatService`의 `Out`이 보내는 이벤트를 모아 두고, 답이 끝나면(정상·오류·창 닫힘 모두) `finally`에서 **질문과 답을 한 번에** 저장한다. 첫 질문이면 대화를 만든다.
- `MessageWindowChatMemory` 대신 `DbChatMemory`: `get()`은 `chat_message` 최근 20개를 읽고 `add()`는 아무것도 안 한다. 그래서 `MessageChatMemoryAdvisor`가 붙어도 두 번 저장되지 않고, 화면 기록과 LLM 문맥이 같은 데이터를 본다. 질문을 답과 함께 나중에 저장하므로, 답을 만드는 동안 문맥에 이번 질문이 두 번 들어가지 않는다.
- API: `GET /api/chat/conversations`, `GET|PATCH|DELETE /api/chat/conversations/{id}`. 요청에 `lang`(auto|ja|en)을 추가했다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| A. Spring AI JDBC ChatMemoryRepository | 공식 starter로 메시지 저장 | 코드가 적다 | 글만 저장해서 근거 카드·버튼을 못 담는다. 화면용 표를 따로 두면 같은 대화가 두 군데 저장된다. 의존성도 는다 |
| B. 브라우저 localStorage | 서버 변경 없음 | 가장 쉽다 | 브라우저를 바꾸면 사라지고, backend 재시작 뒤 LLM 문맥이 끊긴다 |
| C. 메시지마다 바로 저장 | 질문을 먼저 저장 | 중간에 죽어도 질문이 남는다 | Advisor가 문맥에 이번 질문을 한 번 더 붙여 중복된다. 대신 `finally`에서 저장해서 끊겨도 남게 했다 |
| D. 자체 표 + DbChatMemory | (채택) | 한 곳에 저장, meta까지 | — |

## 결과 / 트레이드오프 (Consequences)
- backend를 다시 띄워도 이전 대화 문맥이 이어진다.
- [다시 보내기]를 누르면 실패한 질문·답도 기록에 남는다 (지우지 않는다).
- 저장이 실패해도 채팅 답은 이미 나갔으므로 로그만 남긴다.

## 재검토 조건
- 대화가 수천 개를 넘어 목록 API가 느려지면 → 페이지 나누기
