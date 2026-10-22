# 결과 보고서 — 수업 노트 AI

**번호: G120· 성함: 박소미** · 2026-10-22 제출 · AI 서비스 개발 Mini-project **과제 2. 신규 AI 서비스 개발**
---

## 1. 프로젝트명 및 주제 선정 배경

**수업 노트 AI** — Preply·AmazingTalker에서 1:1로 한국어를 가르치는 선생님이 쓰는 학생 학습관리 AI.

일본인 학생에게 한국어를 가르친 경험에서 출발했다. 온라인 1:1 수업은 수업료가 계속 내려가고 있어서, 학생은 "나를 기억하고 설명을 잘하는 선생님"을 고른다. 그렇지 않은 선생님에게서는 2~3회 만에 떠난다. 1:1 선생님에게는 학생이 계속 남는 것이 곧 수입이다.

그래서 서비스가 내세우는 것은 "준비 시간 단축"보다 **"학생이 떠나지 않게 하는 맞춤 수업과 성장 기록"**이다 ([기획 ADR-0020](docs/planning-adr/0020-primary-metric-draft-quality.md)).

## 2. 해결하고자 하는 문제

| 문제 | 지금 겪는 일 |
|---|---|
| 수업 준비 | 학생마다 모국어·수준·목표가 달라서 자료와 설명을 매번 새로 만든다. 지침서에서 근거를 찾는 데도 시간이 든다 |
| 수업 후 정리 | 기록·피드백·숙제 정리를 미루면, 다음 수업에서 무엇이 약했는지 잊는다 |
| 성장 보여 주기 | 학생이 "늘고 있다"고 느낄 근거(배운 양, 해결한 약점)를 정리해 보여 주기 어렵다 |

세 문제는 하나로 이어진다. 기록이 쌓여야 다음 준비가 빨라지고 학생에게 맞춰지며, 쌓인 기록이 그대로 진도 리포트가 된다.

```
학생 등록 → 수업 준비 → 수업 → 수업 후 기록 → 프로필 갱신 ─┐
   ▲                                                       │
   └──────────────────── 다음 수업 준비 ◀──────────────────┘
```

## 3. 개발 환경 및 기술 스택

| 영역 | 기술 | 왜 골랐나 |
|---|---|---|
| Frontend | Vue 3, Vite, TypeScript, Pinia, PrimeVue, Tailwind | 샘플의 Vue를 이어 쓰되, 화면이 15개를 넘어 단일 HTML 대신 SPA로 나눴다 ([ADR-0003](docs/adr/0003-frontend-stack.md)) |
| Backend | Spring Boot 4, Spring AI 2, Postgres, Flyway | 앱 데이터·API와 채팅 의도 분류를 맡는다. DB는 여기서만 다룬다 ([ADR-0001](docs/adr/0001-service-role-split.md), [ADR-0005](docs/adr/0005-data-access-ownership.md)) |
| AI 서버 | FastAPI, LangGraph | 샘플의 FastAPI + LangGraph 구조를 그대로 이어받았다. 작업별 그래프 4개 |
| LLM | Ollama `qwen3:8b` (로컬), Anthropic은 `.env`로 전환 가능 | API 비용 0, 데모 환경 = 실제 사용 환경 ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)) |
| RAG | macOS Vision OCR, Parent-Child 청크, Ollama `bge-m3` 임베딩, 파일 색인 | 세종학당 PDF에 표·2단 편집이 많아 OCR 품질이 중요했다. 청크 수천 개라 벡터 DB 없이 파일로 충분 ([ADR-0014](docs/adr/0014-teaching-material-rag.md)) |
| 기준 데이터 | 국립국어원 표준 교육과정 문법 336개·어휘 10,635개, Kiwi 형태소 분석 | 학생 수준·예문 수준을 같은 잣대로 재기 위해 ([ADR-0016](docs/adr/0016-standard-level-list-and-item-ids.md)) |
| 실행 추적 | LangSmith + 앱 안 "AI 추적" 탭 | 노드 → 함수 → LLM 호출을 시간 막대로 확인 ([ADR-0028](docs/adr/0028-langsmith-tracing-and-trace-page.md)) |
| 테스트 | pytest (가짜 LLM), JUnit + Testcontainers, vue-tsc | LLM 없이 그래프 분기와 API 계약을 검증 |
| 개발 환경 | macOS (16GB), `scripts/dev.sh` 하나로 전체 기동 | [ADR-0026](docs/adr/0026-single-dev-script.md) |

## 4. 시스템 아키텍처

### 4-1. 전체 구성

```
브라우저 ─▶ frontend :5173 ─▶ backend :8080 ─▶ ai-server :8000 ─▶ LLM (Ollama qwen3:8b)
             (Vue SPA)        (Spring Boot)     (FastAPI+LangGraph)   └▶ RAG 색인 (교재·지침서·핸드북)
                                  │
                                  └─▶ Postgres :5432
```

- 브라우저는 backend만 호출한다. 긴 AI 작업의 진행 상황은 SSE로 ai-server → backend → 브라우저로 중계한다 ([ADR-0006](docs/adr/0006-sse-proxy-path.md)).
- **AI는 DB에 직접 쓰지 않는다.** ai-server는 필요한 데이터를 요청으로 받아 초안만 돌려주고, 저장은 선생님이 승인한 뒤 backend가 한다 ([기획 ADR-0009](docs/planning-adr/0009-hitl-on-all-writes.md)).

![시스템 아키텍처](docs/diagrams/capture-system-architecture/system-architecture.visual-check.1440x900.light.png)

### 4-2. LangGraph 처리 흐름

**수업 준비 그래프** ([lesson_prep/graph.py](ai-server/app/agent/lesson_prep/graph.py))

```
load_profile → load_textbook → plan_lesson(코드) → write_explanations → write_scripts
  → auto_review(1회, 코드 점검=판정 / LLM 점검=참고) → briefing(RAG 근거 + 출처 쪽수)
  → write_slides(15장 틀은 코드, 문구는 LLM 1회) → write_slide_scripts(장마다 따로)
  → human_review(선생님 승인·수정·피드백에서 멈춤)
        ├─ 승인 → 끝
        ├─ 설명 피드백 → write_explanations로
        └─ 슬라이드 피드백 → write_slides로
```

![수업 준비 워크플로](docs/diagrams/capture-lesson-prep-workflow/lesson-prep-workflow.visual-check.1440x900.light.png)

**수업 후 기록 그래프** ([post_lesson/graph.py](ai-server/app/agent/post_lesson/graph.py))

```
extract(메모·녹취록 → 다룬 항목·오류·약점·숙제) → gate → observe(LLM이 장면 인용)
  → judge(코드가 이해도 판정) → write_feedback(학생 메시지) → validate ─┬→ 끝
                                                                    └→ write_feedback 재시도
```

그 밖에 자연어 학생 등록 초안([intake.py](ai-server/app/agent/intake.py)), 교재 근거 문법 질문([grammar_qa.py](ai-server/app/agent/grammar_qa.py))이 있다. 채팅 의도 분류는 Spring AI가 하고, 수업 준비·기록 같은 작업 요청은 해당 화면으로 넘긴다 ([ADR-0010](docs/adr/0010-chat-work-requests-handoff.md)).

### 4-3. 적용한 기술 요소

| 기술 요소 | 적용 여부 | 어디에, 어떻게 |
|---|---|---|
| **RAG** | 적용 | 세종학당 PDF를 Vision OCR → Parent-Child 청크 → `bge-m3` 임베딩으로 파일 색인. 문법은 형태 키 태그(teaches/mentions)로 찾고, 의미 검색은 문화 포인트·브리핑에 쓴다. 답에는 출처 쪽수를 달고, "원문"을 누르면 원본 PDF가 그 쪽으로 열린다 ([ADR-0014](docs/adr/0014-teaching-material-rag.md), [0025](docs/adr/0025-form-key-tags-and-merged-editions.md), [0030](docs/adr/0030-local-pdf-open-via-ai-server.md)) |
| **LangSmith** | 적용 | `call_llm` 한 곳에서 프롬프트 이름·티어·모델을 붙여 추적, RAG 검색과 코드 점검 함수도 `@traceable`. 병렬 LLM 호출이 trace에서 흩어지지 않게 `ContextThreadPoolExecutor` 사용. 앱 안 "AI 추적" 탭에서 트리·시간 막대로 본다 ([ADR-0028](docs/adr/0028-langsmith-tracing-and-trace-page.md)) |
| **모듈화** | 적용 | 서비스 3개(frontend / backend / ai-server)로 역할을 나눴다. ai-server 안은 `agent/`(lesson_prep, post_lesson, grammar_qa, intake), `rag/`, `curriculum/`, `standard/`, `api/`로 나누고, 그래프는 작업별로 따로 둔다 ([ADR-0001](docs/adr/0001-service-role-split.md), [0009](docs/adr/0009-graph-split-and-hitl-location.md)). 프롬프트는 코드 밖 `ai-server/prompts/*.md` |
| **의존성 주입** | 적용 | Spring은 생성자 주입으로 서비스·리포지토리·`ChatClient`를 조립한다. ai-server는 LLM을 `llm.get_model()`/`call_llm()` 한 곳으로 모아, 테스트에서 가짜 LLM으로 바꿔 끼운다 (`tests/conftest.py`) |
| **단위 테스트** | 적용 | ai-server `pytest` **159 passed** (가짜 LLM으로 그래프 분기·API·채점 규칙·RAG 매칭). backend JUnit + Testcontainers 25개 (등록·준비·기록 흐름, 채팅 기록, 라우터) |
| **Agent / 도구 호출** | 적용 | Spring AI 채팅이 질문 종류를 나눠(`RouterService`) 학생 조회 도구(`@Tool` `StudentLookupTools`)를 부르거나 문법 질문을 ai-server로 넘기고, 작업 요청은 화면으로 넘긴다 ([ADR-0010](docs/adr/0010-chat-work-requests-handoff.md)). LangGraph `interrupt()`로 HITL |
| **Multi-Agent** | 일부러 안 씀 | 설명 도우미·수업 준비·챗봇을 에이전트로 나누면 근거 검색을 LLM 판단에 맡기게 된다. 로컬 8B 모델은 도구 선택을 자주 틀려서, 같은 지식 엔진(RAG + 모국어 노트 + 표준 등급)을 정해진 절차로 쓰는 쪽을 골랐다 ([기획 ADR-0024](docs/planning-adr/0024-grammar-qa-chat-p0.md), [ADR-0013](docs/adr/0013-process-over-model.md)) |
| **MCP** | 안 씀 | 도구가 Spring 안의 학생 조회뿐이라 Spring AI `@Tool`로 충분했다. 10장 향후 개선에 적었다 |

### 4-4. 샘플 프로젝트(all_total_vue_student) 대비 재사용·변경

| 샘플 구성 | 이 프로젝트 | 구분 |
|---|---|---|
| `web_chat.html` (Vue 채팅 화면) | Vue 3 SPA 16개 화면 + 플로팅 채팅 위젯·AI 채팅 탭 (같은 대화 공유) | 변경·확장 |
| `server.py` (FastAPI) | `ai-server/app/api/` FastAPI 엔드포인트 (prep, post_lesson, intake, grammar_qa, level_test, report, traces) | 재사용·확장 |
| — | Spring Boot backend 추가 (DB·API·채팅 라우팅) | 신규 |
| `agent/graph.py` (장애 진단 흐름) | 작업별 그래프 4개로 분리 (수업 준비, 수업 후 기록, 등록, 문법 질문) ([ADR-0009](docs/adr/0009-graph-split-and-hitl-location.md)) | 변경 |
| `ollama_llm.py`, `openai_llm.py` | Ollama `qwen3:8b` + Anthropic 전환 경로 | 재사용 (OpenAI → Anthropic) |
| `fake_llm.py` | 가짜 LLM으로 pytest 159개 실행 | 재사용 |
| `session_store.py` (SQLite) | 그래프 체크포인트는 SQLite(`AsyncSqliteSaver`) 유지, 채팅 기록은 Postgres로 ([ADR-0041](docs/adr/0041-chat-history-in-postgres.md)) | 일부 재사용 |
| `mcp_server.py`, `mcp_client.py` | **사용하지 않음.** 교수 자료는 ai-server 안의 RAG 색인으로, 학생·수업 데이터는 backend가 요청에 담아 보낸다 | 대체 |
| `data/` (모니터링·장애 매뉴얼) | 세종학당 교재·지침서·핸드북 OCR 색인, 표준 등급 목록 JSON, 단원 시트, 모국어별 노트 | 교체 |
| LangSmith | 유지 + 앱 안 "AI 추적" 탭 | 재사용·확장 |

| | 처리 흐름 |
|---|---|
| 샘플 | 장애 문의 → 유형 분류 → 모니터링 조회 → 매뉴얼 검색 → 원인 분석 → 답변 |
| 이 서비스 | 학생 선택 → 프로필·이번 과 불러오기 → 구성안(코드) → 설명·대본 → 지침서 근거 브리핑 → 15장 슬라이드 → **선생님 승인** |

### 4-5. 설계 트레이드오프

중심 설계 원칙은 **"정답이 있는 건 코드가, 지식은 자료가, LLM은 고르기·채우기·다듬기만"**이다 ([ADR-0013](docs/adr/0013-process-over-model.md)). 16GB 맥북의 8B 모델로 쓸 만한 결과를 내려면 모델보다 절차를 고쳐야 했다. 슬라이드 틀·등급 판정·이해도 판정·진도 계산은 코드가 하고, LLM은 문구만 쓴다.

| 결정 | 얻은 것 | 대가 |
|---|---|---|
| 수업 구성안(복습·어휘·문법·숙제, 시간 배분)을 LLM 대신 코드 규칙으로 | 결과가 결정적이고 바로 나온다. ID·시간 합계 오류가 없다 | "이번엔 회화 위주로" 같은 특별한 요청은 선생님이 검토 화면에서 고쳐야 한다 |
| 브리핑 근거는 코드가 RAG로 모으고, 출처(책·쪽)도 코드가 붙임 | 선생님이 원문을 확인할 수 있다 ("원문" 버튼으로 그 쪽 PDF가 열림) | 브리핑 품질이 OCR·구역 인식 품질에 달려 있다 |
| 데모·평가도 로컬 `qwen3:8b` ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)) | API 비용 0, 데모 = 실제 환경 | 설명·대본 같은 긴 생성의 품질과 속도는 로컬 모델 수준. 수업 준비 한 번에 AI 대기 약 10분 |
| 자동 검토는 한 번만, LLM 점검은 "참고 의견" ([ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)) | 흔들리는 LLM 판정 때문에 다시 만드는 일이 없어 시간이 예측된다 | LLM이 잡던 문제(문체 섞임 등)를 자동으로 고치지 않는다 |
| 이해도는 LLM이 장면을 인용(observe)하고 코드가 판정(judge) ([ADR-0033](docs/adr/0033-observe-judge-understanding.md)) | 판정 근거가 화면에 남는다 | 인용을 못 찾으면 판정이 비어 있다 |
| 모든 쓰기에 선생님 승인 (HITL) | 잘못된 AI 초안이 학생 기록을 오염시키지 않는다 | 선생님 클릭이 늘어난다 |
| RAG 저장소를 pgvector·Chroma 대신 파일 색인 | ai-server가 DB에 접근하지 않는다(ADR-0005 유지), 의존성 감소 | 대규모 자료에는 맞지 않는다. 지금 규모(청크 수천 개)에서만 유효 |
| Multi-Agent·MCP를 쓰지 않음 | 로컬 8B 모델에서도 근거 검색이 흔들리지 않는다 | 도구가 늘면 라우팅 코드가 커진다 |

## 5. 주요 구현 기능

| 기능 | 무엇을 하나 | AI가 하는 일 / 코드가 하는 일 |
|---|---|---|
| 학생 등록 | 자연어 설명("일본인 대학생 유이, 드라마 좋아함, 받침 발음 약함")으로 칸을 채운 초안 → 선생님 확인 후 저장 | AI: 칸 채우기 / 선생님: 수준·학습 목적 확정 |
| 체험수업 레벨테스트 | 한글 읽기 + 1~6급 문항, 화면 공유용 학생 창 (문항만 보이고 답은 숨김) | 코드: 추천 등급 계산 |
| 수업 준비 | 15장 슬라이드 구성안 + 장별 대본, 지침서 근거 브리핑(출처 쪽수), 모국어 화자가 자주 틀리는 점, 문화 포인트, 범주별 승인·수정·피드백 | 코드: 구성안·근거·출처 / AI: 설명·대본·문구 |
| 수업 후 기록 | 메모나 녹취록(.txt) → 다룬 항목, 잘한 점·틀린 점, 약점 추가·해결, 숙제, 학생 메시지(일본어·영어 + 한국어 번역), 항목별 이해도 → 다음 수업 복습에 반영 | AI: 추출·장면 인용 / 코드: 이해도 판정, 승인된 항목만 반영 |
| 문법 질문 챗봇 | "-아서랑 -니까 뭐가 달라?" → 비교표 → 핵심 차이 → 교재 원문 근거. 근거가 없으면 "AI 설명 · 검수 필요"로 따로 표시 ([ADR-0043](docs/adr/0043-grammar-answer-comparison-table.md), [기획 ADR-0036](docs/planning-adr/0036-ai-explanation-when-no-textbook-evidence.md)) | 코드: 형태 찾기·근거 검색·예문 / AI: 쓰임 한 줄 |
| 채팅 기록 | Postgres에 저장, LLM 문맥(ChatMemory)도 같은 표에서 읽음. 전용 탭과 플로팅 위젯이 같은 대화를 씀 ([ADR-0041](docs/adr/0041-chat-history-in-postgres.md), [0042](docs/adr/0042-nav-chat-tab-shared-conversation.md)) | — |
| 진도 리포트 | 기간별 새로 배운 문법·어휘, 표준 등급별 양, 해결한 약점, 학생에게 보낼 메시지 초안 | 코드: 숫자와 문장 모두 |
| 대시보드 | 월간 수업 달력, 날짜를 누르면 그날 수업의 준비 상태 | — |
| 어휘·문법 등급 목록 | 표준 문법 336개·어휘 10,635개 검색, 문법마다 교재 몇 과에서 배우는지 | — |
| 단원 시트 | 「세종학당 한국어」 1·2는 지침서에서, 3A~6B는 본책 쪽에서 과별 문법·어휘를 뽑아 표준 ID로 연결 | 코드 |
| 지표 | 주 지표: AI 초안을 그대로 승인한 비율 / 보조: 준비·정리 시간 (AI 대기와 선생님 작업 분리) | 서비스가 자동 기록 |

## 6. 프로그램 실행 방법

```bash
cp .env.example .env
bash scripts/setup_ollama.sh   # qwen3:8b 준비
bash scripts/dev.sh            # Postgres(docker) + ai-server + backend + frontend
python3 scripts/seed_demo.py   # (선택) 데모 학생
```

접속: http://localhost:5173 · 데모 시나리오와 자세한 설정은 [README.md](README.md)

## 7. 테스트 결과 및 실행 화면

### 7-1. 자동 테스트

| 대상 | 내용 | 결과 |
|---|---|---|
| ai-server `uv run pytest` | 가짜 LLM으로 그래프 분기, 권위 게이트, API 계약, 레벨테스트 채점, 진도 계산, 문법 형태 찾기 | **159 passed** (2026-10-22, 6.4초) |
| backend `./gradlew test` | Testcontainers Postgres + 가짜 ai-server로 학생 등록 → 수업 준비 → 승인 흐름, 채팅 기록, 라우터 | 테스트 25개 |
| frontend `npm run typecheck` | 타입 검사 | — |

### 7-2. 수업 후 기록 추출 정확도 (실제 LLM 호출)

[ai-server/eval/](ai-server/eval/)에 가상 메모 16개(함정 케이스 포함) 평가셋을 두고 정답과 비교했다.

| 실행 | 모델 | 케이스 | 항목 ID·약점 변경 일치율 (목표 0.8) | 약점 변경 | 숙제 |
|---|---|---|---|---|---|
| 2026-10-19 | Claude Sonnet | 16 | 0.969 | 0.938 | 1.0 |
| 2026-10-20 | 로컬 `qwen3:8b` | 3 | 0.922 | 1.0 | 1.0 |

- 로컬 모델 실행은 3개 케이스만 돌렸다. 두 값은 케이스 수가 달라 바로 비교하지 않는다 (자세한 비교는 8-3).
- 로컬 모델에서 틀린 케이스(c01)는 "1~10번 단어"를 15개로 펼친 것이었다 (정밀도 0.79).

### 7-3. 주요 기능별 테스트 입력과 결과

| 기능 | 입력 | 확인한 결과 |
|---|---|---|
| 학생 등록 | "일본인 대학생 유이, 한글은 읽음, 드라마 좋아하고 내년에 서울 여행 가고 싶대. 받침 발음이 약함" | 모국어(ja)·목표·관심사·약점 칸이 채워진 초안(로컬 모델 약 22초). 수준은 비워 두고 "레벨테스트 결과로 골라 주세요"로 안내 |
| 레벨테스트 | 한글 5개 맞음, 1급 맞음, 2급 일부 틀림 | 추천 "표준 2급", 학생 창이 문항을 따라감 |
| 수업 준비 | 유이(ja, 1급·여행), Jay(en, 입문·회화) | 같은 과라도 브리핑의 모국어별 실수·예상 질문이 다르게 나옴, 출처 쪽수 표시 |
| 수업 후 기록 | "3과 1~10 단어 함. -습니다 잘함. 을/를 받침 구분 계속 틀림. 숙제는 연습문제 2번" | 다룬 항목, 잘한 점, 틀린 점, 숙제, 일본어 메시지 초안. 이미 있는 약점은 추가 제안을 지움 |
| 채팅 | "유이 요즘 약한 거 뭐야?" / "유이 다음 수업 40분으로 준비해줘" | 약점 조회 답변 / [수업 준비 화면 열기] 버튼 |
| 문법 질문 | "너라면 너니까 너라서 너거나 뭐가 달라?" | 같은 앞부분을 떼서 -라면/-니까/-라서/-거나 비교표, 교재 근거 9개 표시 ([TS-0005](docs/troubleshooting/0005-listed-conjugations-and-related-form-evidence.md) 이후) |

### 7-4. 오류·예외 상황

| 상황 | 동작 |
|---|---|
| 교재에 근거가 없는 문법 질문 | "근거 없음"으로 끝내지 않고 AI 설명을 "검수 필요"로 따로 표시, 모국어 설명은 만들지 않음 ([기획 ADR-0036](docs/planning-adr/0036-ai-explanation-when-no-textbook-evidence.md)) |
| 슬라이드 대본 중 한 장 생성 실패 | 나머지 장은 남기고 실패한 장만 표시 ([ADR-0035](docs/adr/0035-slide-script-node.md)) |
| 자동 검토의 코드 점검 실패 | 다시 만들지 않고 검토 화면에 경고 ([ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)) |
| 학생 메시지 검증 실패 | `validate → write_feedback`으로 다시 생성 |
| 수준 칸 없이 학생 저장 | API가 거부 (DB는 기존 학생 때문에 nullable, API는 필수) ([ADR-0017](docs/adr/0017-student-level-fields-and-level-test.md)) |
| 이해도 장면이 원문에 없음 | 원문에 없거나 다룬 항목이 아닌 장면은 버리고 화면에 몇 개 버렸는지 알림 |

### 7-5. 실행 화면

> 2026-10-22, `bash scripts/dev.sh`로 띄운 로컬 서비스(데모 학생 3명)를 1440×900 화면으로 캡처했다.

**대시보드** — 월간 수업 달력. 날짜를 누르면 오른쪽에 그날 수업의 준비 단계(준비 시작 → 수업안 확정 → 수업 기록 승인)가 보인다.

![대시보드](docs/report-images/01-dashboard.png)

**학생 등록** — 왼쪽에 체험수업 메모를 붙여 넣고 "초안 만들기"를 누르면 AI가 오른쪽 칸을 채운다. 현재 수준은 AI가 정하지 않고 레벨테스트로 고르게 한다.

![학생 등록 초안](docs/report-images/03-student-new.png)

**레벨테스트** — 선생님 창에서 문항을 누르면, 화면 공유용 학생 창에 문항만 크게 뜬다 (예시 답·등급은 숨김).

![레벨테스트 선생님 창](docs/report-images/05-level-test.png)

![레벨테스트 학생 창](docs/report-images/06-level-test-screen.png)

**수업 준비 목록** — 다음 수업이 가까운 학생부터, 준비 상태와 약점을 함께 보여 준다.

![수업 준비 목록](docs/report-images/07-prep.png)

**수업 준비 — 선생님 브리핑** — 문법 설명 포인트는 지침서 근거(출처 쪽수)로, 모국어 화자가 자주 틀리는 점·예상 질문은 "AI 생성 · 검수 필요"로 구분해 보여 준다. 아래에는 코드가 짠 50분 수업 진행이 이어진다.

![수업 준비 브리핑](docs/report-images/08-lesson-review.png)

**수업 준비 — 15장 슬라이드 구성안 + 장별 대본** — 장을 펼치면 소요 시간·목표·진행·질문과 예상 답변·학생이 어려워할 때/잘할 때 대응이 나온다.

![15장 구성안](docs/report-images/08b-slide-plan.png)

**수업 준비 — 범주별 검토** — 복습·새 어휘·새 문법·숙제를 범주마다 승인·수정·피드백한다. 학생 모국어(영어)로 쓴 개인화 설명과 수업 대본, 새로 만든 예문 표시.

![범주별 검토](docs/report-images/08c-review-approve.png)

**수업 후 기록** — 메모에서 다룬 항목·잘한 점·틀린 점·숙제·학생 메시지(일본어 + 한국어 번역)를 뽑고, 체크한 항목만 승인해 학생 프로필에 반영한다.

![수업 후 기록](docs/report-images/09-lesson-record.png)

**문법 질문 챗봇** — 비교표 → 핵심 차이 → 교재 근거(책·과·쪽) 순서. 표의 줄을 누르면 근거 원문이 펼쳐진다.

![문법 질문](docs/report-images/10-chat-grammar.png)

**어휘·문법 등급 목록** — 국립국어원 표준 교육과정 문법 336개·어휘 10,635개. 문법마다 교재 몇 과에서 배우는지 연결했다.

![등급 목록](docs/report-images/11-standard.png)

**진도 리포트** — 기간별 수업 수, 새로 배운 문법·단어, 표준 등급별 진도, 해결한 약점. 숫자와 학생 메시지 모두 코드가 계산한다.

![진도 리포트](docs/report-images/12-report.png)

**지표** — 주 지표(AI 초안을 그대로 승인한 비율)와 보조 지표(준비·정리 시간, AI 대기와 선생님 작업 분리).

![지표](docs/report-images/13-metrics.png)

**AI 추적** — LangSmith 기록을 앱 안에서 본다. 문법 질문 한 번(10.8초)이 형태 찾기 → 근거 검색 → LLM 답변(8.4초) → 예문 점검 순으로 돈 것이 보인다.

![AI 추적 목록](docs/report-images/14-traces.png)

![AI 추적 실행 흐름](docs/report-images/14-traces-tree.png)

**커리큘럼** — 세종학당 교육과정과 표준 등급의 대응, 학습 목적(페르소나)별 중심 교재.

![커리큘럼](docs/report-images/15-curriculum.png)

## 8. Before / After 비교

### 8-1. 기능 비교 (기존 `korean-ppt-ai-agent` → 수업 노트 AI)

| | Before | After |
|---|---|---|
| 형태 | 터미널 CLI 에이전트 | 웹 서비스 (대시보드 + 채팅) |
| 범위 | 수업 자료 생성만 | 등록 → 레벨테스트 → 준비 → 기록 → 리포트 고리 |
| 결과물 | PPT 파일 | 15장 구성안 + 장별 대본 + 근거 브리핑 (PPT는 만들지 않음) |
| 근거 | 교재 JSON 3개 과 | 세종학당 자료 RAG + 출처 쪽수, 「한국어」 1~6B 단원 시트 |
| 구성안 | LLM이 작성, 자동 검토에서 틀리면 재시도 루프 | 코드 규칙, 자동 검토는 한 번 |
| 검토 | CLI `interrupt` | 화면에서 범주별 승인·수정·피드백 |
| 모델 | 큰 모델 전제 | 로컬 8B 모델 |

### 8-2. 실측 (서비스가 자동 기록한 값, 2026-10-22 기준)

**보조 지표: 시간** (`GET /api/metrics/time`)

| | 기록 수 | 평균 전체 | AI 대기 | 선생님 작업 | 기준 시간 (Before) | 감소율 |
|---|---|---|---|---|---|---|
| 수업 준비 | 4회 | 15.0분 | 10.0분 | 5.0분 | _(입력 필요)_ | _(입력 후 계산)_ |
| 수업 후 정리 | 2회 | 15.0분 | 1.0분 | 14.1분 | _(입력 필요)_ | _(입력 후 계산)_ |

**주 지표: AI 초안을 그대로 승인한 비율** (`GET /api/metrics/quality`)

| | 대상 | 그대로 둔 비율 | 목표 가설 |
|---|---|---|---|
| 수업안 첫 검토 승인 | 4개 범주 (수업 1회) | 100% (4/4) | 70% 이상 |
| 수업 후 기록 초안 유지 | 항목 33개 (기록 2회) | 100% (33/33) | 80% 이상 |

읽을 때 주의할 점:
- 표본이 작다 (수업 준비 4회, 기록 2회). 모두 개발자 본인이 데모 학생으로 잰 값이다.
- 기준 시간(AI 없이 준비할 때)을 아직 입력하지 않아 감소율이 계산되지 않았다. 지표 화면에서 입력하면 바로 계산된다.
- 승인 비율 100%는 품질의 대리 지표다. 바빠서 대충 승인해도 올라가므로 시간 지표와 함께 본다 ([기획 ADR-0020](docs/planning-adr/0020-primary-metric-draft-quality.md)).

### 8-3. 수업 후 기록 추출 — 모델 비교 (`eval/run_eval.py`, 같은 데이터셋)

| 지표 | Sonnet (2026-10-19, 16케이스) | qwen3:8b 로컬 (2026-10-20, 3케이스) |
|---|---|---|
| PRD 지표 (항목 ID·약점 변경 일치율, 목표 0.8) | 0.969 | 0.922 |
| 다룬 항목 F1 | 1.0 | 0.844 |
| 약점 변경 정확도 | 0.938 | 1.0 |
| 숙제 정확도 | 1.0 | 1.0 |
| 케이스당 시간 (c01~c03 평균) | 5.4초 | 36.2초 |
| 비용 | 과금 | 0원 (로컬) |

- 결과 파일: `ai-server/eval/results/20261019-135936.md`, `20261020-094929.md`
- 두 실행은 케이스 수가 다르고, 로컬 실행만 피드백 메시지 생성까지 포함(`--with-feedback`)이라 시간은 그대로 비교할 수 없다. 정확도는 목표(0.8)를 넘기면서 비용을 0으로 줄였다는 근거로만 쓴다 ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)).

### 8-4. 같은 입력, 고치기 전·후 (트러블슈팅)

| 입력 | Before | After |
|---|---|---|
| 「세종학당 한국어」 5A~6B 문형 (예: ko5a 10과 "과연 -을까") | 4건이 1·2급 항목으로 잘못 연결, 5A~6B 과 절반은 문법 0개 | 잘못 연결 0건, 0개였던 과 일부가 잡힘 ("...은 -기 나름이다" 5급, "...에 따르면" 4급) — [TS-0006](docs/troubleshooting/0006-compound-patterns-matched-to-beginner-items.md) |
| "너라면, 너라서, 너니까 차이" | 형태를 못 찾음 | 어미로 찾고 교재 근거와 함께 답 (7-5 문법 질문 화면) — [TS-0005](docs/troubleshooting/0005-listed-conjugations-and-related-form-evidence.md) |
| "-아서랑 -니까 차이" | `-어/아서` "근거 없음" | 두 형태 모두 교재 근거로 답 — [TS-0001](docs/troubleshooting/0001-grammar-qa-shorthand-and-invented-form.md) |

## 9. 개발 과정의 문제점 및 해결 방법

### 9-1. 설계를 바꾼 문제

| 문제 | 처음 시도 | 바꾼 방법 |
|---|---|---|
| 로컬 8B 모델은 항목 선택·시간 합계를 한 번에 지키지 못했고, 합계가 틀리면 최대 3번 다시 계획했다 | 프롬프트로 제약을 강조 → 100% 지켜지지 않음. 예시 프롬프트를 넣자 예시 내용을 그대로 베낌 | 구성안을 코드 규칙으로, 브리핑 지식은 지침서 RAG로 ([ADR-0013](docs/adr/0013-process-over-model.md), [ADR-0020](docs/adr/0020-local-model-for-demo-too.md)) |
| 흔들리는 LLM 검토 판정이 재시도를 일으켜 준비 시간이 두 배 | 재시도 한도 줄이기 검토 | 검토는 한 번, LLM 점검은 참고 의견 ([ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)) |
| 모국어별 실수 설명을 LLM이 그럴듯하게 지어냄 | — | 표준 ID 기준 데이터에서 꺼내고, 데이터에 없을 때만 LLM + "검수 필요" ([ADR-0022](docs/adr/0022-l1-notes-data.md)) |

### 9-2. 트러블슈팅 ([docs/troubleshooting/](docs/troubleshooting/README.md))

| # | 문제 | 원인 → 해결 |
|---|---|---|
| 0001 | 문법 질문이 질문에 없던 `-어/아서`를 "근거 없음"으로 답함 | 줄임 표기(`-아/어서`)를 펼치지 않음, LLM이 형태를 지어냄 → 줄임 표기 펼치기, 질문에 없는 형태는 버리기 |
| 0002 | PDF "원문"이 늘 첫 쪽으로 열림 | `open -a`가 URL의 `#page`를 버림 → `osascript`로 Chrome에 URL 직접 전달 |
| 0003 | 인쇄 33쪽이 PDF 33쪽(과 표지)으로 열림 | 쪽 대응표 충돌 → 인식된 쪽 번호부터 채우도록 수정 |
| 0004 | 불규칙 용언(춥다·듣다)이 어휘 등급에서 빠짐 | Kiwi 태그가 `VA-I`·`VV-I` → 태그 앞부분만 비교 |
| 0005 | "너라면, 너라서"는 형태를 못 찾고, 관련형은 근거 없음 | 나열한 활용형의 공통 앞부분을 떼고, 대표형 교재 구역도 근거로 찾기 ([ADR-0037](docs/adr/0037-listed-conjugations-and-head-form-evidence.md)) |
| 0006 | 5~6급 문형 "과연 -을까"가 1급 "-을까"로 잡힘 | 질문용 매칭 함수가 앞 낱말을 버리고 잘라 맞춤 → 여러 조각 문형은 조각별로 맞추고, 3급 이상 교재는 3급 이상 조각만 매칭 ([ADR-0040](docs/adr/0040-unit-sheets-from-textbook-3a-6b.md)) |

### 9-3. 느낀 점

- 좋은 모델보다 **절차를 정해 두는 쪽**이 효과가 컸다. 로컬 8B 모델에 판단을 맡기면 흔들렸고, 틀은 코드가 잡고 LLM에는 작은 칸만 맡기니 결과가 안정됐다.
- 결정을 ADR로 남기니 기획이 바뀔 때 무엇을 뒤집는지 분명해졌다. 기획 ADR 36개, 기술 ADR 44개, 트러블슈팅 기록 6개를 남겼다.
- 실제 선생님으로 일하고 있어서 "이걸 수업 전에 정말 볼까?"를 기준으로 기능을 걸렀다 (예: PPT를 만들지 않고 구성안 + 대본으로 바꿈).

## 10. 한계점 및 향후 개선 방향

### 한계
- **사용자**: 선생님 한 명이 로컬에서 쓰는 서비스다. 로그인·권한이 없다.
- **속도**: 로컬 모델이라 수업 준비 한 번에 AI 대기가 평균 10분이다. 미리 준비해 두는 사용 방식을 전제로 한다.
- **데이터 검수**: 단원 시트, 모국어별 노트, 레벨테스트 문항 대부분이 검수 전 초안이다. 화면에 "검수 전"으로 표시한다.
- **예문**: 기획은 "예문은 자료에서 찾고 등급으로 거른다"([기획 ADR-0017](docs/planning-adr/0017-examples-from-materials-not-generated.md))인데, 수업 준비의 설명 노드는 아직 LLM이 예문을 만든다 (7-5 범주별 검토 화면의 "새 예문" 표시). 예문 등급도 어휘만 보고 문법은 보지 않는다.
- **평가**: 로컬 모델 추출 정확도는 3개 케이스로만 쟀고, 실측 지표도 표본이 작다. 선생님이 검수한 정답 케이스가 아직 없다. 학생 리텐션(본래 목표)은 아직 잴 수 없다.
- **RAG**: OCR이 macOS에서만 돈다. 교재 PDF·색인은 저작권 때문에 저장소에 없어서, 다른 환경에서는 색인을 다시 만들어야 한다.
- **Multi-Agent·MCP**: 쓰지 않았다. 자료 접근이 ai-server 안 RAG 하나라 지금은 충분하지만, 도구가 늘면 라우팅 코드가 커진다.

### 향후 개선
1. 학습 계획(목표·경로·속도) — 수업 기록의 이해도로 "천천히 / 빨리 / 계획 다시 보기" 제안 (설계 완료, 구현 대기, [기획 ADR-0031](docs/planning-adr/0031-learning-plan-and-pace-suggestions.md))
2. 예문을 세종학당 자료에서 찾아 학생 등급으로 거르기
3. 실제 학생 수업에 써서 기준 시간·승인 비율 표본 늘리기, 평가셋 16개 전체를 로컬 모델로 다시 재기
4. 음성 메모·STT를 서비스 안에서 받기
5. 다른 교재(페르소나별 중심 교재)의 과별 데이터 확대
6. 교재·학생 조회를 MCP 서버로 묶어 다른 클라이언트에서도 쓰기
