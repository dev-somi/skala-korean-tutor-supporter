# ADR-0027: 채팅 프론트는 고정 SSE 계약 + 개발용 mock 스트림으로 RAG와 따로 만든다
- 상태: Accepted (2026-10-21)
- 관련 모듈: `frontend/src/api/types.ts` (채팅 SSE 계약), `frontend/src/api/mock/`, `frontend/src/api/endpoints.ts`, `frontend/src/components/ChatWidget.vue`
- 관련 ADR: [ADR-0006](0006-sse-proxy-path.md), [ADR-0024](0024-japanese-handbook-and-grammar-qa.md), [ADR-0025](0025-form-key-tags-and-merged-editions.md)

## 배경 (Context)
- 문법 질문 챗봇(기획 ADR-0024)은 Vue → Spring `/chat/stream` → ai-server `/grammar-qa`(RAG) 순서로 돈다.
- RAG(색인·형태 키·검색)를 계속 고치는 중이라 ai-server 응답이 느리거나(로컬 모델로 20초 이상) 엉뚱하다. 2026-10-21 "이거 어떻게 가르쳐?"에는 질문에 없던 `-어/아서`를 근거 없음으로 돌려줬다.
- 그때마다 채팅 화면 작업이 멈춘다. 화면은 응답 **모양**만 알면 되고 RAG 품질과는 상관이 없다.

## 결정 (Decision)
1. **채팅 SSE 이벤트를 계약으로 고정한다.** `routing_decided / sources / token / action / error / done`과 `GrammarSources` 타입을 `api/types.ts` 한 곳에 두고 주석으로 표를 단다. 응답 모양을 바꾸려면 이 타입과 fixture를 먼저 고친다.
2. **프론트 안에 mock 스트림을 둔다** (`api/mock/chatMock.ts`). Spring `ChatService`와 같은 순서로 이벤트를 보내고, RAG 대기 시간을 흉내 내 1.5~3초 늦춘다. 중단(AbortSignal)을 지킨다.
3. **fixture는 지어내지 않고 실제 ai-server 응답을 저장한다** (`api/mock/fixtures/*.json`). 질문 글자로 시나리오를 고른다: 근거 충분(-아서/-(으)니까), 학생 등급 밖(사는/살던, 유이), 근거 없음, 형태 못 찾음, 오류, 일반 질문.
4. **켜는 법은 주소의 `?mock`** (개발 서버에서만). `.env`·package.json을 바꾸지 않아 dev.sh를 다시 띄울 필요가 없다. 프로덕션 빌드는 `import.meta.env.DEV`가 false라 mock 코드와 fixture가 빠진다. mock일 때 채팅 창 머리에 `MOCK` 태그를 보여 가짜 답으로 데모하지 않게 한다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| ai-server stub 엔드포인트 | `/grammar-qa`가 고정 JSON을 돌려줌 | Spring 경로까지 실제로 탄다 | 서버 3개를 다 띄워야 하고, RAG를 고치는 파일과 같은 곳을 건드린다 |
| MSW (Mock Service Worker) | 브라우저에서 fetch를 가로챔 | 실제 fetch·SSE 파서까지 탄다 | 의존성·서비스 워커 파일 추가. SSE 스트림 흉내가 번거롭다. 채팅 한 곳만 필요하다 |
| VITE_CHAT_MOCK 환경 변수 | `.env`로 켜고 끔 | 흔한 방식 | `.env`를 바꾸면 dev.sh를 다시 띄워야 한다 (CLAUDE.md) |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: RAG가 깨져 있어도 채팅 화면(진행 단계, 중단, 재시도, 근거 카드 비교)을 만들고 볼 수 있다.
- 좋은 점: fixture가 계약의 예시 역할을 한다. RAG 쪽이 모양을 바꾸면 타입 검사(`npm run typecheck`)에서 어긋남이 드러난다.
- 대가: mock은 `sse.ts` 파서와 Spring을 거치지 않는다. 합치기 전에 `?mock` 없이 같은 질문으로 실제 경로를 꼭 확인한다.
- 대가: fixture는 저장한 날의 RAG 결과다. 색인이 바뀌면 다시 찍어야 실제와 같다.

## 재검토 조건
- 다른 화면(수업 준비 SSE 등)도 백엔드 없이 만들 일이 많아지면 → MSW로 옮겨 한 방식으로 모은다
- 계약 어긋남이 자주 나면 → ai-server 응답을 fixture와 비교하는 테스트를 둔다
