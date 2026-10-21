# 개인 AI 서비스 프로젝트용 참고 노트
> 출처: AI캠퍼스 *AI Capstone* 교안 (2026.10.16, 253p) — "장애 진단 Agent" 시나리오를 기반으로 Multi-Agent · MCP · SSE · 관측성을 다룸
> 이 노트는 그중 **개인 AI 서비스를 직접 만들 때 그대로 가져다 쓸 수 있는 것**만 추린 것. `(p.N)`은 원본 PDF 페이지 번호.

---

## 0. 한눈에 보는 레퍼런스 아키텍처 (p.3)

```
Client(React + Vercel AI SDK useChat)
   ⇅  SSE (/chat/stream)
Backend(FastAPI, lifespan에서 Agent 1회 생성)
   ⇅
Agent(LangGraph Supervisor 그래프)
   route → (simple) chat_answer → END
         → (complex) plan → gate → research ⇄ replan_check
                         → analysis(조건부) → write ⇄ validate → finalize
   ├─ MCP Server (Tool / Resource / Prompt) — subprocess + stdio
   ├─ Checkpointer (대화 상태: Postgres)
   └─ LangSmith (trace · 평가)
```

**개인 프로젝트로 가져올 핵심 뼈대**: `라우팅 게이트 → 계획 → 실행(도구) → 충분성 체크 → 작성 → 검증 → 마무리`.
처음부터 다 만들 필요는 없고, 아래 7장 로드맵 순서로 붙여 나가면 된다.

---

## 1. ADR(Architecture Decision Record) 습관 들이기 (p.7–8)

혼자 하는 프로젝트일수록 "내가 왜 이렇게 만들었지?"를 잊는다. **대안이 있었고 트레이드오프를 따져본 결정만** ADR로 남긴다 (단순 버그 수정은 제외).

### 템플릿 (`adr/0001-xxx.md`)
```markdown
# ADR-000N: <결정 제목>
- 상태: Proposed | Accepted | Superseded
- 관련 모듈:

## 배경 (Context)
## 결정 (Decision)
## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
## 결과 / 트레이드오프 (Consequences)
## 재검토 조건 (언제 이 결정을 다시 볼 것인가)
```
> 포인트: **"재검토 조건"** 칸이 있으면 나중에 규모가 커졌을 때 무엇을 바꿔야 할지 바로 보인다.

---

## 2. 그대로 참고할 만한 설계 결정 12가지 (p.8–22)

| # | 질문 | 교안의 채택안 | 왜 | 개인 프로젝트 적용 팁 |
|---|---|---|---|---|
| 1 | MCP 서버를 어디에 둘까 (p.8) | **subprocess + stdio** | 표준 client 재사용, 프로세스 격리 | 단일 배포면 이걸로 충분. 여러 백엔드 인스턴스가 공유해야 할 때 원격 HTTP로 전환 |
| 2 | RAG 검색을 어디서 (p.9) | **Agent가 Tool로 필요할 때만 호출** | "안녕"에도 검색 돌리는 낭비 제거, LLM이 쿼리 재구성 | 고정 RAG 파이프라인보다 비용·품질 모두 유리 |
| 3 | MCP 기능 분류 (p.11) | **Tool / Resource / Prompt 분리** | 기준: 결과가 매번 달라지면 Tool, URI로 식별되는 정적 문서는 Resource, 호출 절차를 표준화하려면 Prompt | 설계 단계에서 이 기준표를 정해두기 |
| 4 | 실시간 전송 (p.12) | **SSE** | 서버→클라 단방향이면 WebSocket은 과함. 기존 HTTP·프록시 재사용, `curl -N`으로 디버깅 | 챗봇 스트리밍은 거의 항상 SSE |
| 5 | 프론트 이벤트 포맷 (p.13) | **useChat + Custom Transport** | SDK는 쓰되 전송·파싱 계층만 교체 → Plan/Task 같은 도메인 구조를 잃지 않음 | 단순 챗봇이면 SDK 표준 포맷, "생각 과정 카드" 등 보여줄 거면 커스텀 |
| 6 | 복잡한 요청 조율 (p.14) | **Supervisor + Sub-agent** | 진행 상황을 단계별로 보여줄 수 있고, 역할별로 다른 모델·도구 배정 가능 | 역할 2~4개 규모면 완전분산 A2A는 과설계 |
| 7 | 단순 질문 처리 (p.15) | **백엔드 Routing 게이트 (저가 모델)** | 인사말에 Planning 돌리는 비용 제거, 길이 휴리스틱보다 신뢰도 높음 | **가장 먼저 넣을 최적화** |
| 8 | 분석 책임 위치 (p.16) | **전담 Analysis + 이중 게이트** | LLM 판단(게이트1) + 코드 필터(게이트2) 둘 다 통과해야 실행 | → 4장 "권위 게이트" 패턴 |
| 9 | 계획 수정 (p.17) | **상한형 Dynamic Replanning** (`MAX_REPLAN_ROUNDS=1`) | 정보 부족을 스스로 보완하되 무한 루프·비용 폭증 차단 | 모든 루프에 **상한**을 둔다 |
| 10 | 최종 답변 검증 (p.18) | **전담 Validator (LLM-as-Judge)** | 규칙 기반은 의미 판단 불가, 사람 검수는 실시간성 해침 | 재작성 최대 2~3회 |
| 11 | 실패 처리 (p.19) | **4-Layer + Graceful Degradation** | Tool/Orchestration/Application/Presentation 계층별 처리, 부분 결과라도 응답 | 프론트에서 "재시도 가능" vs "복구 불가" 구분 표시 |
| 12 | 비용·지연 (p.20) | **모델 티어링 + 병렬 실행** | 비용은 티어링으로, latency는 `asyncio.gather`로 — 서로 다른 축 | 라우팅·계획은 mini 모델, 조사·작성은 고품질 모델 |
| 13 | 품질 평가 (p.21) | **LangSmith + 혼합 Evaluator** | 휴리스틱(빠르고 결정적) + LLM-judge(의미 기반) 상호보완 | 기대 토픽 포함 여부 같은 건 휴리스틱으로 |
| 14 | 대화 상태 저장 (p.22) | **PostgreSQL (AsyncPostgresSaver)** | 재시작 내구성 + 다중 인스턴스 공유 | **개인 단일 서버라면 SQLite도 OK** (교안도 "단일 인스턴스 재시작엔 문제없음"이라고 평가). 다중 인스턴스 갈 때 Postgres로 |

---

## 3. 백엔드 구현 패턴

### 3-1. FastAPI lifespan으로 Agent 1회만 생성 (p.25–29)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = await build_agent()   # 서버 시작 시 1회
    yield                                    # 요청마다 app.state.agent 재사용
    # 종료 시 정리(커넥션 풀, MCP subprocess 등)

app = FastAPI(lifespan=lifespan)
```
- 생성 비용 큰 객체(LLM 클라이언트, 그래프, MCP 연결)는 요청마다 만들지 않는다 = 싱글턴 효과.

### 3-2. Pydantic 하나로 4곳 검증 (p.32)
`BaseModel` 하나로 API 입출력 검증 + LLM 구조화 출력(`with_structured_output`) + SSE 이벤트 스키마 + JSON 스키마를 동시에 얻는다.

### 3-3. SSE 스트리밍 엔드포인트 (p.99–105)
```python
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        event_generator(req),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
```
- LangGraph `astream(..., stream_mode=["messages", "updates"])`로 두 종류 이벤트를 한 스트림에서 구분 수신 (p.103)
  - `messages` → 토큰 청크 → `TokenEvent`, tool_call_chunks → `ToolCallStartEvent`
  - `updates` → 노드 상태 변화 → `ToolCallEndEvent` (결과는 200자로 잘라 전송)
  - 종료 시 `DoneEvent(thread_id)`
- **이벤트 순서 설계** (p.146): `routing_decided` → `plan_created` → `task_list_created` …
  라우팅 결과를 **가장 먼저** 보내야 프론트가 "단순 답변 UI"인지 "Plan 카드 UI"인지 미리 결정 가능.

### 3-4. 의존성 주입 & Factory (p.211–212, 219)
- 헬퍼 함수가 전역 `client`, `MODEL`을 몰래 참조하지 않게 → `call_llm(prompt, client, model)`처럼 **인자로 명시**. 테스트·모델 교체가 쉬워짐.
- Checkpointer 같은 교체 가능 컴포넌트는 `persistence/checkpointer.py`의 `create_checkpointer()`(asynccontextmanager) 한 곳에서만 생성. MemorySaver → SQLite → Postgres 교체 시 **파일 1개만** 수정.

### 3-5. 모듈 구조 (p.217–218)
2,400줄짜리 `bot.py` 하나 대신 역할별 모듈로 분리 → 폴더·파일·함수명이 그대로 구조를 설명하게.
예: `api/`, `agent/` (supervisor_graph, nodes), `mcp_server/`, `persistence/`, `schemas/`, `tests/`

---

## 4. Agent 품질·안정성 패턴

### 4-1. 권위 게이트 (Authoritative Gate) — LLM 판단을 코드가 강제 정정 (p.148–150)
```python
decision = await fast_llm.with_structured_output(PlanDecision).ainvoke([...])
spec_tasks = decision.tasks

# LLM이 needs_analysis=False인데 analysis task를 넣는 실수를 해도 코드가 정정
if not decision.needs_analysis:
    spec_tasks = [t for t in spec_tasks if t.agent != "analysis"]
```
> **원칙**: 플래그 필드는 신뢰하되, 그 플래그를 기준으로 실제 실행 목록은 코드가 다시 쓴다. 프롬프트 지시만으로는 보장이 없다.

### 4-2. 충분성 체크 + 재계획 루프 (p.155–161)
- `replan_check_node`: 평가만 담당 (`is_sufficient` 판단)
- `replan_node`: 부족한 부분(gap) 전용 task만 추가
- `MAX_REPLAN_ROUNDS`로 상한. 상한 도달 시 강제로 다음 단계 진행.
- 평가와 재계획을 **노드로 분리**하면 trace에서 어디서 판단했는지 보인다.

### 4-3. Validator (LLM-as-a-Judge) (p.165–169)
4가지 기준을 **한 번의 호출**로 평가:
| 기준 | 질문 |
|---|---|
| Relevance | 질문과 관련 있는 답인가? |
| Completeness | 요청에 필요한 내용을 다 담았나? |
| Clarity | 이해하기 쉬운가? |
| Domain Appropriateness | 해당 도메인 기준에 맞나? |

- 출력 스키마는 단순하게: `is_acceptable: bool` + `reasoning: str`
- 불합격 시 reasoning을 feedback으로 Writing에 되돌려 재작성 (횟수 상한 필수)
- 내 서비스 도메인에 맞게 4번째 기준을 바꿔 쓰면 됨

### 4-4. 무한 루프 가드 (p.170–171)
`max_iter=10`, `max_time=60s` 같은 이중 상한. 초과 시 `early_stopping="generate"`로 **현재까지 정보로 답을 생성**하고 우아하게 종료.

### 4-5. 에러 처리 (p.175–178, 203–205)
- **Transient(일시적) 오류만 재시도**: `asyncio.TimeoutError` 등 → Exponential Backoff (0.5s → 1.5s, `max_retries=2`)
- **영구 오류는 즉시 실패**: `ValueError`, 잘못된 인자 → 재시도해도 같은 결과이므로 `ToolError(code="TOOL_EXECUTION_ERROR")`로 바로 변환
- 재시도 다 써도 실패 → `ToolError(TOOL_TIMEOUT_AFTER_RETRY)`
- **Error 격리 + Partial Result**: task별 `try/except ToolError` → 그 task만 `failed`, 나머지는 계속. `finalize_node`가 성공한 것만으로 부분 응답 조립
  ("일부 정보는 확보했으나 task-3은 완료하지 못했습니다…")
- 주의: 공유 자원(MCP 서버 자체)이 죽으면 격리해도 전부 실패한다.

---

## 5. 비용·성능 최적화

### 5-1. 모델 티어링 (p.183–184)
| 단계 | 모델 | 비고 |
|---|---|---|
| Routing / Planning | 저가 모델 (예: gpt-4o-mini) | 단순 분류·분해 |
| Research / Writing | 고품질 모델 (예: gpt-4o) | 품질이 체감되는 곳 |

교안 예시: Planning만 mini로 바꿔도 **Planning 비용 -97%, 전체 -12%**. 비용 공식 `C_total = Σ(tokens × p_model)`으로 단계별 계산해 보고 결정.
> 모델명은 교안 예시일 뿐 — 현재 쓰는 공급사의 저가/고가 티어로 대응시키면 된다.

### 5-2. 병렬 실행 (p.188–202)
```python
results = await asyncio.gather(*[research_agent(t) for t in tasks])
```
독립적인 task 3개면 순차 대비 latency가 크게 줄어든다 (fan-out / fan-in).

---

## 6. 실전 함정 체크리스트 (교안의 "주의점" 페이지 모음)

- [ ] **uvicorn `--reload`는 개발 전용** (p.35) — 운영에선 `--workers N`만. `--reload`+`--workers` 동시 사용은 기동 실패.
- [ ] **MCP 도구 docstring 품질** (p.46) — LLM은 설명만 보고 도구를 고른다. 등록 전 체크: 입력 형식(타입+의미) / 반환 형식(타입+구조) / 제약·기본값.
  - ❌ `"""검색한다."""` → ✅ `"""query로 source(internal_docs|web) 안의 문서를 검색해 상위 5개 제목을 반환한다."""`
- [ ] **MCP Resource 캐시** (p.48) — "정적"은 보장이 아니라 우연. 응답에 `last_modified`나 content-hash를 포함해 클라이언트가 캐시 유효성 판단.
- [ ] **MCP Prompt는 자동 호출되지 않는다** (p.52) — 사용자가 명시적으로 트리거하는 것. LLM이 스스로 불러야 하면 Tool로 감싸서 재노출.
- [ ] **SSE 프록시 버퍼링** (p.115) — 로컬에선 잘 되다가 nginx 뒤에서 한 번에 몰려옴. 앱 헤더(`X-Accel-Buffering: no`) **+** 프록시 설정(`proxy_buffering off; proxy_cache off;`) 둘 다. 스테이징에서 `curl -N`으로 타이밍 확인.
- [ ] **프론트(Zod)·백엔드(Pydantic) 검증 불일치** (p.117) — 공유 상수(`shared/constraints.json`)나 OpenAPI 자동 생성으로 단일 소스화. 서버 검증은 항상 필요.
- [ ] **asyncio 안에서 블로킹 호출 금지** (p.194) — `requests.post` 하나가 이벤트 루프 전체를 멈춤. `httpx.AsyncClient` 사용 또는 `run_in_executor`.
- [ ] **로컬 모듈명이 표준 라이브러리를 가림** (p.223) — 프로젝트 루트에 `random.py`, `json.py` 등 금지. 패키지(`myapp/`) 하위로.
- [ ] **로그 필드명 표준화** (p.237) — 서비스마다 `user_id` vs `uid` 섞이면 검색에서 누락. 공통 로깅 유틸로 필드명 고정.
- [ ] **trace_id 연결** (p.229) — 메트릭·트레이스·로그를 각각 모으는 것과 연결하는 것은 다르다. OpenTelemetry로 trace_id 포맷 통일.

---

## 7. 관측성 & 평가 (p.225–251)

### 7-1. 관측성 3기둥
| 기둥 | 용도 | 개인 프로젝트 최소 구성 |
|---|---|---|
| Metrics | 추세(요청 수, 에러율) — 사용자 신고보다 먼저 알려줌 | 요청 수 · 에러율 · 응답 시간 |
| Logs | 무슨 일이 있었나 | **구조화 로그(JSON)** + 고정 필드명 |
| Traces | 요청이 거친 경로·단계별 소요 시간 | LangSmith가 LLM 부분은 자동 처리 |

### 7-2. LangSmith 활용 (p.238–251)
```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
os.environ["LANGCHAIN_PROJECT"] = "my-ai-service-dev"   # 실행을 한 대시보드에 모음
```
- **Run**: 실행 1건의 최소 단위, 부모-자식 트리 (그래프 → 노드 → LLM 호출 → tool 호출)
- **Project**: Run 묶음 (dev / prod 분리 추천)
- **Dataset**: 평가용 입력·기대출력 모음 → `client.evaluate()`로 반복 실행해 **변경 전후 비교**
- **Hub**: 프롬프트 버전 관리 (v1, v2, v3…)

### 7-3. 평가 데이터셋 만드는 흐름 (p.245–248)
1. 내 문서로 저가 LLM에게 QA 쌍 합성 생성 (JSON)
2. `reviewed=False`로 저장 → 직접 검수한 항목만 데이터셋에 편입
3. LangSmith Dataset 등록 → `evaluate()` 실행
4. Evaluator = 휴리스틱(기대 토픽 포함?) + LLM-judge(품질)

> 프롬프트나 모델을 바꿀 때마다 같은 데이터셋으로 돌려야 "정말 좋아졌는지" 숫자로 안다.

---

## 8. 개인 프로젝트 적용 로드맵 (제안)

교안 전체를 한 번에 구현하면 과설계가 되기 쉽다. 아래 순서로 필요해질 때 붙이는 걸 권장.

1. **MVP**: FastAPI(lifespan) + LangGraph 단일 Agent + Tool 몇 개 + SSE 스트리밍 + MemorySaver
2. **비용 절감**: Routing 게이트(저가 모델) 추가 → 단순 질문은 즉시 응답
3. **영속화**: Checkpointer Factory 도입 → SQLite (다중 인스턴스 필요 시 Postgres)
4. **관측**: LangSmith 연결 + 구조화 로그
5. **안정성**: `with_retry`(transient만) + task별 에러 격리 + 루프 상한
6. **품질**: Validator 노드 + 평가 데이터셋 20~50개
7. **확장**: 복잡한 요청이 많아지면 Supervisor + Sub-agent, Dynamic Replanning, 병렬 실행
8. **도구 표준화**: 외부 연동이 늘면 MCP 서버(Tool/Resource/Prompt)로 분리

각 단계에서 대안을 고민했다면 ADR 한 장씩 남기기.

---
*참고: 원본은 OCR 처리된 슬라이드 PDF라 코드 일부는 슬라이드 이미지를 보고 옮겨 적었다. 실제 라이브러리 API는 사용하는 버전 문서로 한 번 더 확인할 것.*
