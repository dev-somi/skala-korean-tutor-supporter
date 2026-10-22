# 결과 보고서 — 수업 노트 AI (ver2)

박소미 · 2026-10-22 · AI 서비스 개발 Mini-project **과제 2. 신규 AI 서비스 개발**

> 이 보고서는 과제 안내(7장 "최종 제출물 구성")의 10개 항목 순서를 따른다.
> 평가 항목별로 어디를 보면 되는지는 아래 표에 정리했다.

| 평가 항목 (배점) | 보고서 위치 |
|---|---|
| 기능 구현 완성도 (30) | 5장 주요 구현 기능, 7장 테스트 결과 |
| 기술 요소 반영 (30) | 3장 기술 스택과 선택 이유, 4장 아키텍처·그래프 흐름, 4-3 샘플 프로젝트 대비 재사용·변경 |
| 한계 및 트레이드오프 설명 (20) | 4-4 설계 트레이드오프, 10장 한계 |
| Before / After 실측 비교 (보너스 10) | 8장 |

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

시각 자료: [docs/diagrams/system-architecture.html](docs/diagrams/system-architecture.html), [docs/diagrams/lesson-prep-workflow.html](docs/diagrams/lesson-prep-workflow.html)

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

**수업 후 기록 그래프** ([post_lesson/graph.py](ai-server/app/agent/post_lesson/graph.py))

```
extract(메모·녹취록 → 다룬 항목·오류·약점·숙제) → gate → observe(LLM이 장면 인용)
  → judge(코드가 이해도 판정) → write_feedback(학생 메시지) → validate ─┬→ 끝
                                                                    └→ write_feedback 재시도
```

그 밖에 자연어 학생 등록 초안([intake.py](ai-server/app/agent/intake.py)), 교재 근거 문법 질문([grammar_qa.py](ai-server/app/agent/grammar_qa.py))이 있다. 채팅 의도 분류는 Spring AI가 하고, 수업 준비·기록 같은 작업 요청은 해당 화면으로 넘긴다 ([ADR-0010](docs/adr/0010-chat-work-requests-handoff.md)).

### 4-3. 샘플 프로젝트(all_total_vue_student) 대비 재사용·변경

| 샘플 구성 | 이 프로젝트 | 구분 |
|---|---|---|
| `web_chat.html` (Vue 채팅 화면) | Vue 3 SPA 16개 화면 + 플로팅 채팅 위젯·AI 채팅 탭 (같은 대화 공유) | 변경·확장 |
| `server.py` (FastAPI) | `ai-server/app/api/` FastAPI 엔드포인트 (prep, post_lesson, intake, grammar_qa, level_test, report, traces) | 재사용·확장 |
| — | Spring Boot backend 추가 (DB·API·채팅 라우팅) | 신규 |
| `agent/graph.py` (장애 진단 흐름) | 작업별 그래프 4개로 분리 (수업 준비, 수업 후 기록, 등록, 문법 질문) ([ADR-0009](docs/adr/0009-graph-split-and-hitl-location.md)) | 변경 |
| `ollama_llm.py`, `openai_llm.py` | Ollama `qwen3:8b` + Anthropic 전환 경로 | 재사용 (OpenAI → Anthropic) |
| `fake_llm.py` | 가짜 LLM으로 pytest 158개 실행 | 재사용 |
| `session_store.py` (SQLite) | 그래프 체크포인트는 SQLite(`AsyncSqliteSaver`) 유지, 채팅 기록은 Postgres로 ([ADR-0041](docs/adr/0041-chat-history-in-postgres.md)) | 일부 재사용 |
| `mcp_server.py`, `mcp_client.py` | **사용하지 않음.** 교수 자료는 ai-server 안의 RAG 색인으로, 학생·수업 데이터는 backend가 요청에 담아 보낸다 | 대체 |
| `data/` (모니터링·장애 매뉴얼) | 세종학당 교재·지침서·핸드북 OCR 색인, 표준 등급 목록 JSON, 단원 시트, 모국어별 노트 | 교체 |
| LangSmith | 유지 + 앱 안 "AI 추적" 탭 | 재사용·확장 |

샘플의 흐름과 이 서비스의 흐름을 나란히 놓으면 다음과 같다.

| | 처리 흐름 |
|---|---|
| 샘플 | 장애 문의 → 유형 분류 → 모니터링 조회 → 매뉴얼 검색 → 원인 분석 → 답변 |
| 이 서비스 | 학생 선택 → 프로필·이번 과 불러오기 → 구성안(코드) → 설명·대본 → 지침서 근거 브리핑 → 15장 슬라이드 → **선생님 승인** |

수업 준비 노드의 뼈대는 내가 먼저 만들어 둔 `korean-ppt-ai-agent`(수업 자료 생성 CLI)에서 가져왔다 ([기획 ADR-0001](docs/planning-adr/0001-extend-existing-agent.md)).

### 4-4. 설계 트레이드오프

이 프로젝트의 중심 설계 원칙은 **"정답이 있는 건 코드가, 지식은 자료가, LLM은 고르기·채우기·다듬기만"**이다 ([ADR-0013](docs/adr/0013-process-over-model.md)). 16GB 맥북의 8B 모델로 쓸 만한 결과를 내려면 모델보다 절차를 고쳐야 했다.

| 결정 | 얻은 것 | 대가 |
|---|---|---|
| 수업 구성안(복습·어휘·문법·숙제, 시간 배분)을 LLM 대신 코드 규칙으로 | 결과가 결정적이고 바로 나온다. ID·시간 합계 오류가 없다 | "이번엔 회화 위주로" 같은 특별한 요청은 선생님이 검토 화면에서 고쳐야 한다 |
| 브리핑 근거는 코드가 RAG로 모으고, 출처(책·쪽)도 코드가 붙임 | 선생님이 원문을 확인할 수 있다 ("원문" 버튼으로 그 쪽 PDF가 열림) | 브리핑 품질이 OCR·구역 인식 품질에 달려 있다 |
| 데모·평가도 로컬 `qwen3:8b` ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)) | API 비용 0, 데모 = 실제 환경 | 설명·대본 같은 긴 생성의 품질과 속도는 로컬 모델 수준. 수업 준비 한 번에 AI 대기 약 10분 |
| 자동 검토는 한 번만, LLM 점검은 "참고 의견" ([ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)) | 흔들리는 LLM 판정 때문에 다시 만드는 일이 없어 시간이 예측된다 | LLM이 잡던 문제(문체 섞임 등)를 자동으로 고치지 않는다 |
| 이해도는 LLM이 장면을 인용(observe)하고 코드가 판정(judge) ([ADR-0033](docs/adr/0033-observe-judge-understanding.md)) | 판정 근거가 화면에 남는다 | 인용을 못 찾으면 판정이 비어 있다 |
| 모든 쓰기에 선생님 승인 (HITL) | 잘못된 AI 초안이 학생 기록을 오염시키지 않는다 | 선생님 클릭이 늘어난다 |
| RAG 저장소를 pgvector·Chroma 대신 파일 색인 | ai-server가 DB에 접근하지 않는다(ADR-0005 유지), 의존성 감소 | 대규모 자료에는 맞지 않는다. 지금 규모(청크 수천 개)에서만 유효 |

## 5. 주요 구현 기능

| 기능 | 무엇을 하나 | AI가 하는 일 / 코드가 하는 일 |
|---|---|---|
| 학생 등록 | 자연어 설명("일본인 대학생 유이, 드라마 좋아함, 받침 발음 약함")으로 칸을 채운 초안 → 선생님 확인 후 저장 | AI: 칸 채우기 / 선생님: 수준·학습 목적 확정 |
| 체험수업 레벨테스트 | 한글 읽기 + 1~6급 문항, 화면 공유용 학생 창 (문항만 보이고 답은 숨김) | 코드: 추천 등급 계산 |
| 수업 준비 | 15장 슬라이드 구성안 + 장별 대본, 지침서 근거 브리핑(출처 쪽수), 모국어 화자가 자주 틀리는 점, 문화 포인트, 범주별 승인·수정·피드백 | 코드: 구성안·근거·출처 / AI: 설명·대본·문구 |
| 수업 후 기록 | 메모나 녹취록(.txt) → 다룬 항목, 잘한 점·틀린 점, 약점 추가·해결, 숙제, 학생 메시지(일본어·영어 + 한국어 번역), 항목별 이해도 → 다음 수업 복습에 반영 | AI: 추출·장면 인용 / 코드: 이해도 판정, 승인된 항목만 반영 |
| 문법 질문 챗봇 | "-아서랑 -니까 뭐가 달라?" → 비교표 → 핵심 차이 → 교재 원문 근거. 근거가 없으면 "AI 설명 · 검수 필요"로 따로 표시 | 코드: 형태 찾기·근거 검색·예문 / AI: 쓰임 한 줄 |
| 진도 리포트 | 기간별 새로 배운 문법·어휘, 표준 등급별 양, 해결한 약점, 학생에게 보낼 메시지 초안 | 코드: 숫자와 문장 모두 |
| 대시보드 | 월간 수업 달력, 수업별 준비 상태 색 | — |
| 어휘·문법 등급 목록 | 표준 문법 336개·어휘 10,635개 검색, 문법마다 교재 몇 과에서 배우는지 | — |
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
| ai-server `uv run pytest` | 가짜 LLM으로 그래프 분기, 권위 게이트, API 계약, 레벨테스트 채점, 진도 계산, 문법 형태 찾기 | **158 passed** (2026-10-22, 4.5초) |
| backend `./gradlew test` | Testcontainers Postgres + 가짜 ai-server로 학생 등록 → 수업 준비 → 승인 흐름 | 테스트 25개 |
| frontend `npm run typecheck` | 타입 검사 | — |

### 7-2. 수업 후 기록 추출 정확도 (실제 LLM 호출)

[ai-server/eval/](ai-server/eval/)에 가상 메모 16개(함정 케이스 포함) 평가셋을 두고 정답과 비교했다.

| 실행 | 모델 | 케이스 | 항목 ID·약점 변경 일치율 (목표 0.8) | 약점 변경 | 숙제 |
|---|---|---|---|---|---|
| 2026-10-19 | Claude Sonnet | 16 | 0.969 | 0.938 | 1.0 |
| 2026-10-20 | 로컬 `qwen3:8b` | 3 | 0.922 | 1.0 | 1.0 |

- 로컬 모델 실행은 3개 케이스만 돌렸다. 두 값은 케이스 수가 달라 바로 비교하지 않는다 ([ADR-0020](docs/adr/0020-local-model-for-demo-too.md)).
- 로컬 모델에서 틀린 케이스(c01)는 "1~10번 단어"를 15개로 펼친 것이었다 (정밀도 0.79).

### 7-3. 주요 기능별 테스트 입력과 결과

| 기능 | 입력 | 확인한 결과 |
|---|---|---|
| 학생 등록 | "일본인 대학생 유이, 한글은 읽음, 드라마 좋아하고 내년에 서울 여행 가고 싶대. 받침 발음이 약함" | 이름·모국어(ja)·관심사·약점 칸이 채워진 초안, 선생님이 수준을 골라 저장 |
| 레벨테스트 | 한글 5개 맞음, 1급 맞음, 2급 일부 틀림 | 추천 "표준 2급", 학생 창이 문항을 따라감 |
| 수업 준비 | 유이(ja, 1급·여행), Jay(en, 입문·회화) | 같은 과라도 브리핑의 모국어별 실수·예상 질문이 다르게 나옴, 출처 쪽수 표시 |
| 수업 후 기록 | "3과 1~10 단어 함. -습니다 잘함. 을/를 받침 구분 계속 틀림. 숙제는 연습문제 2번" | 다룬 항목 ID, 약점 추가(을/를), 숙제, 일본어 메시지 초안 → 승인 후 학생 카드 약점 갱신 |
| 채팅 | "유이 요즘 약한 거 뭐야?" / "유이 다음 수업 40분으로 준비해줘" | 약점 조회 답변 / [수업 준비 화면 열기] 버튼 |
| 문법 질문 | "너라면, 너라서, 너니까 차이" | 같은 앞부분을 떼서 -라면/-라서/-니까 비교표, 교재 근거 표시 ([TS-0005](docs/troubleshooting/0005-listed-conjugations-and-related-form-evidence.md) 이후) |

### 7-4. 오류·예외 상황

| 상황 | 동작 |
|---|---|
| 교재에 근거가 없는 문법 질문 | "근거 없음"으로 끝내지 않고 AI 설명을 "검수 필요"로 따로 표시, 모국어 설명은 만들지 않음 ([기획 ADR-0036](docs/planning-adr/0036-ai-explanation-when-no-textbook-evidence.md)) |
| 슬라이드 대본 중 한 장 생성 실패 | 나머지 장은 남기고 실패한 장만 표시 ([ADR-0035](docs/adr/0035-slide-script-node.md)) |
| 자동 검토의 코드 점검 실패 | 다시 만들지 않고 검토 화면에 경고 ([ADR-0021](docs/adr/0021-auto-review-llm-advisory.md)) |
| 학생 메시지 검증 실패 | `validate → write_feedback`으로 다시 생성 |
| 수준 칸 없이 학생 저장 | API가 거부 (DB는 기존 학생 때문에 nullable, API는 필수) ([ADR-0017](docs/adr/0017-student-level-fields-and-level-test.md)) |

### 7-5. 실행 화면

_(대시보드 · 수업 준비 브리핑 · 15장 구성안 · 수업 후 기록 · 문법 질문 · 지표 화면 캡처 첨부)_

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
| 0006 | 5~6급 문형 "과연 -을까"가 1급 "-을까"로 잡힘 | 3급 이상 교재는 조각 문형을 3급 이상 조각만 매칭 ([ADR-0040](docs/adr/0040-unit-sheets-from-textbook-3a-6b.md)) |

## 10. 한계점 및 향후 개선 방향

### 한계
- **사용자**: 선생님 한 명이 로컬에서 쓰는 서비스다. 로그인·권한이 없다.
- **속도**: 로컬 모델이라 수업 준비 한 번에 AI 대기가 평균 10분이다. 미리 준비해 두는 사용 방식을 전제로 한다.
- **데이터 검수**: 단원 시트, 모국어별 노트, 레벨테스트 문항 대부분이 검수 전 초안이다. 화면에 "검수 전"으로 표시한다.
- **예문**: 기획은 "예문은 자료에서 찾고 등급으로 거른다"([기획 ADR-0017](docs/planning-adr/0017-examples-from-materials-not-generated.md))인데, 수업 준비의 설명 노드는 아직 LLM이 예문을 만든다. 예문 등급도 어휘만 보고 문법은 보지 않는다.
- **평가**: 로컬 모델 추출 정확도는 3개 케이스로만 쟀고, 실측 지표도 표본이 작다. 학생 리텐션(본래 목표)은 아직 잴 수 없다.
- **RAG**: OCR이 macOS에서만 돈다. 교재 PDF·색인은 저작권 때문에 저장소에 없어서, 다른 환경에서는 색인을 다시 만들어야 한다.
- **MCP**: 샘플의 MCP 구조는 쓰지 않았다. 자료 접근이 ai-server 안 RAG 하나라 외부 도구 연동이 필요해지면 다시 본다.

### 향후 개선
1. 학습 계획(목표·경로·속도) — 수업 기록의 이해도로 "천천히 / 빨리 / 계획 다시 보기" 제안 (설계 완료, [기획 ADR-0031](docs/planning-adr/0031-learning-plan-and-pace-suggestions.md))
2. 예문을 세종학당 자료에서 찾아 학생 등급으로 거르기
3. 실제 학생 수업에 써서 기준 시간·승인 비율 표본 늘리기, 평가셋 16개 전체를 로컬 모델로 다시 재기
4. 다른 교재(페르소나별 중심 교재)의 과별 데이터 확대
