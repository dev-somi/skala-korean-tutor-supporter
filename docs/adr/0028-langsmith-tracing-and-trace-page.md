# ADR-0028: ai-server 실행을 LangSmith로 추적하고, 앱의 "AI 추적" 탭에서 Spring을 거쳐 읽는다
- 상태: Accepted (2026-10-21)
- 관련 모듈: `ai-server/app/agent/lesson_prep/llm.py`, `ai-server/app/agent/lesson_prep/nodes.py` (`run_parallel`), `ai-server/app/api/traces.py`, `backend/.../trace/TraceController.java`, `frontend/src/pages/TracesPage.vue`
- 관련 ADR: [ADR-0001](0001-service-role-split.md) (Spring AI·FastAPI 역할 분담), [ADR-0005](0005-data-access-ownership.md) (브라우저는 Spring만 부른다), [ADR-0007](0007-llm-provider-tiering.md) (모델 티어), [기획 ADR-0011](../planning-adr/0011-virtual-data-only.md) (가상 데이터만)

## 배경 (Context)
- LLM이 언제, 어떤 프롬프트로, 몇 토큰·몇 초를 쓰는지 볼 방법이 없었다. `.env.example`에 LangSmith 키 자리만 주석으로 있었다.
- 수업 준비 그래프는 노드 8개, 범주별 병렬 LLM 호출, 코드 점검이 섞여 있어서 "어디서 오래 걸렸나 / 어디서 틀렸나"를 로그만으로 찾기 어렵다.
- 과제 평가 기준에 LangSmith가 들어 있다 (`docs/reference/AI 서비스 Mini-Project.pdf`).
- 매번 LangSmith 웹에 로그인하지 않고 앱 안에서 바로 보고 싶다.

## 결정 (Decision)
1. **ai-server만 추적한다.** `.env`의 `LANGSMITH_TRACING`·`LANGSMITH_API_KEY`·`LANGSMITH_PROJECT`로 켠다. 키가 없으면 아무것도 보내지 않는다.
2. 이름표를 붙인다: LLM 호출은 `call_llm` 한 곳에서 `run_name=프롬프트 이름`, `tags=[tier]`, `metadata={prompt, tier, model}`. 그래프 실행은 `run_name=lesson_prep | post_lesson`(+ `thread_id`), 그래프가 아닌 진입점은 `@traceable`(`student_intake`, `grammar_qa`).
3. 코드 함수도 트리에 보이게 `@traceable`을 몇 곳에만 단다: RAG 검색(`retriever`: `search`, `find_by_form`, `get_sections`), 코드 점검(`tool`: `validate_draft`, `extract_forms`, `collect_evidence`, `check_examples`).
4. `run_parallel`은 `langsmith.utils.ContextThreadPoolExecutor`를 쓴다. 일반 `ThreadPoolExecutor`는 contextvars를 넘기지 않아 병렬 LLM 호출이 부모 그래프와 떨어진 trace로 흩어진다.
5. 화면 경로는 `Vue /traces → Spring GET /api/traces[/{id}] → ai-server GET /traces[/{id}] → LangSmith API`. 키는 ai-server에만 있다. ai-server가 run 목록을 `parent_run_id`로 트리로 엮고, 맨 위 실행 기준 시작 시각(`start_offset_ms`)을 붙여 준다. 저장하지 않는다.
6. 화면은 요약 카드(실행 수·에러·평균 시간·토큰/비용) + 실행 목록 + 선택한 실행의 들여쓰기 트리와 시간 막대(run_type별 색). 자세한 내용은 LangSmith 링크로 넘긴다. 새 프론트 라이브러리는 쓰지 않는다.

## 검토한 대안 (Alternatives)
| 대안 | 설명 | 장점 | 기각 이유 |
|---|---|---|---|
| LangSmith 웹 링크만 | 탭에서 LangSmith 프로젝트로 이동만 | 만들 게 거의 없다 | 앱 안에서 바로 못 보고, 로그인이 필요하다. 사용자가 앱 안 트리 화면을 골랐다 |
| 프론트가 LangSmith API 직접 호출 | Vite 환경변수에 키 | Spring·ai-server를 안 고친다 | 키가 브라우저로 나간다. "브라우저는 Spring만" 규칙(ADR-0005)과 어긋난다 |
| Langfuse 자체 호스팅 | docker-compose에 Langfuse 추가 | 데이터가 밖으로 안 나간다 | 컨테이너가 하나 더(Postgres·ClickHouse 포함) 늘고, 과제 기준이 LangSmith다 |
| 채팅까지 ai-server로 옮기고 전부 추적 | Spring AI를 빼고 LLM을 한 곳에 | 추적 한 군데, LLM 설정도 한 군데 | `chat/` 약 500줄(라우터·Tool Calling·SSE·대화 메모리) 재작성 + ADR-0001 뒤집기. 마감(10/22) 직전에 위험하다 |
| Spring AI도 OpenTelemetry로 함께 추적 | Micrometer → OTLP → LangSmith | 채팅 라우터도 보인다 | Gradle 의존성·설정이 늘고 이번 범위에서 검증할 시간이 없다. 재검토 조건으로 둔다 |

## 결과 / 트레이드오프 (Consequences)
- 좋은 점: 수업 준비 한 번이 "노드 → 검색·코드 점검 → LLM 호출" 순서와 시간 막대로 보인다. 병렬 호출이 실제로 겹쳐 도는지도 보인다.
- 좋은 점: 프롬프트 이름·티어·모델이 붙어 있어 LangSmith에서 프롬프트별로 걸러 볼 수 있다 (나중의 Dataset 평가에도 쓴다).
- 대가: **Spring AI 채팅(라우터·조회 답변·일반 답변)은 추적되지 않는다.** 화면에도 그렇게 적었다.
- 대가: 프롬프트와 입력(학생 프로필 포함)이 LangSmith 클라우드로 나간다. 가상 데이터만 쓰므로([기획 ADR-0011](../planning-adr/0011-virtual-data-only.md)) 받아들인다. 실제 학생 데이터를 쓰게 되면 끄거나 자체 호스팅으로 바꾼다.
- 대가: 화면이 열릴 때마다 LangSmith API를 부른다 (목록 50개). 느리면 캐시를 둔다.
- 대가: 로컬 Ollama는 비용이 없어서 비용 칸은 비어 있다.

## 재검토 조건
- 채팅 라우터의 비용·지연을 봐야 할 때 → Spring AI OpenTelemetry 추적을 추가한다 (`micrometer-tracing-bridge-otel` + `opentelemetry-exporter-otlp`, 엔드포인트 `https://api.smith.langchain.com/otel/v1/traces`).
- 실제 학생 데이터를 쓰게 될 때 → 추적을 끄거나 자체 호스팅 도구로 옮긴다.
