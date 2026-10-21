# Architecture Decision Records

대안이 있었고 트레이드오프를 따져 본 결정만 남긴다. 템플릿은 [참고노트](../reference/AI_Capstone_개인프로젝트_참고노트.md) 1장.

| 번호 | 제목 | 상태 |
|---|---|---|
| [0001](0001-service-role-split.md) | Spring AI 백엔드와 FastAPI AI 서버의 역할 분담 | Accepted |
| [0002](0002-app-database.md) | 앱 데이터 저장소로 PostgreSQL 사용 | Accepted |
| [0003](0003-frontend-stack.md) | 프론트엔드 스택 — Vue 3 + Vite + TS + Pinia + PrimeVue + Tailwind | Accepted |
| [0004](0004-monorepo-layout.md) | `ai-service-test` 모노레포 구조 | Accepted |
| [0005](0005-data-access-ownership.md) | DB는 Spring만 다루고, FastAPI는 요청으로 데이터를 받는다 | Accepted |
| [0006](0006-sse-proxy-path.md) | SSE 경로 — Vue → Spring(SseEmitter) → FastAPI | Accepted |
| [0007](0007-llm-provider-tiering.md) | LLM 공급사 Anthropic + 모델 티어링 | Accepted |
| [0008](0008-local-dev-runtime.md) | 개발·데모 실행 방식 — Postgres만 Docker | Accepted |
| [0009](0009-graph-split-and-hitl-location.md) | 그래프를 작업별로 나누고, HITL 위치를 그래프마다 다르게 둔다 | Accepted |
| [0010](0010-chat-work-requests-handoff.md) | 채팅의 작업 요청은 화면으로 넘긴다 | Accepted |
| [0011](0011-frontend-library-versions.md) | 프론트 라이브러리는 이전 메이저 버전으로 고정 | Accepted |
| [0012](0012-local-ollama-for-dev.md) | 개발 중에는 로컬 Ollama(qwen3:8b), 데모·평가만 Anthropic | Accepted, 데모·평가 항목만 Superseded by 0020 |
| [0013](0013-process-over-model.md) | 좋은 모델보다 정형화된 절차 — LLM은 작은 칸만 채운다 | Accepted |
| [0014](0014-teaching-material-rag.md) | 교수 자료 RAG — Vision OCR + Parent-Child + 파일 색인 | Accepted |
| [0015](0015-lesson-prep-ends-at-approval.md) | 수업 준비 그래프는 승인에서 끝나고, 7단계 틀은 briefing 노드가 붙인다 | Accepted |
| [0016](0016-standard-level-list-and-item-ids.md) | 표준 등급 목록은 ai-server 파일 데이터 + 교재 대응표, 예문 등급은 Kiwi로 판정 | Accepted (2026-10-20) |
| [0017](0017-student-level-fields-and-level-test.md) | 학생 수준 칸은 DB nullable·API 필수, 레벨테스트 문항과 판정은 ai-server | Accepted (2026-10-20), 결정 7·8(결과 저장 안 함, 쿼리로 등록)만 Superseded by 0019 |
| [0018](0018-progress-report-computed-in-ai-server.md) | 진도 리포트는 Spring이 기록을 모아 보내고 ai-server가 계산 (저장 안 함, 템플릿 문장) | Accepted (2026-10-20) |
| [0019](0019-level-test-student-screen-and-results.md) | 학생 화면은 BroadcastChannel 별도 창, 레벨테스트 결과는 `level_test_result`에 저장하고 apply로 반영 | Accepted (2026-10-20) |
| [0020](0020-local-model-for-demo-too.md) | 데모·평가도 로컬 qwen3:8b — 품질은 절차와 데이터로 맞춘다 | Accepted (2026-10-20) |
| [0021](0021-auto-review-llm-advisory.md) | 자동 검토는 다시 만들지 않는다 — 코드 점검은 경고, LLM 점검은 참고 의견 | Accepted (2026-10-20) |
| [0022](0022-l1-notes-data.md) | 모국어별 지식은 표준 ID 기준 데이터 — Claude 초안 + 선생님 검수, LLM은 없는 문법만 | Accepted (2026-10-20) |
| [0023](0023-culture-candidates-rag-and-teacher-pick.md) | 문화 후보는 의미 검색 + LLM 1회 정리, 선택은 화면에서만 | Accepted (2026-10-20) |
| [0024](0024-japanese-handbook-and-grammar-qa.md) | 일본어판 핸드북 두 번 OCR 색인 + 표준 ID 필터 경로로 문법 질문에 답한다 | Accepted (2026-10-21), 대응표·표준 ID 필터만 Superseded by 0025 |
| [0025](0025-form-key-tags-and-merged-editions.md) | 교수 자료 색인 v2 — 문법은 형태 키 태그(teaches/mentions)로 찾고, 언어판은 한 덩어리로 합친다 | Accepted (2026-10-21) |
| [0026](0026-single-dev-script.md) | 개발 실행은 scripts/dev.sh 하나로 — 한 터미널, 저장하면 자동 반영(devtools 포함), 로그는 .dev-logs/ | Accepted (2026-10-21) |
| [0027](0027-chat-frontend-mock-stream.md) | 채팅 프론트는 고정 SSE 계약 + 개발용 mock 스트림(`?mock`)으로 RAG와 따로 만든다 | Accepted (2026-10-21) |
| [0028](0028-langsmith-tracing-and-trace-page.md) | ai-server 실행을 LangSmith로 추적하고, "AI 추적" 탭에서 Spring을 거쳐 트리로 본다 (Spring AI 채팅은 아직 제외) | Accepted (2026-10-21) |
| [0029](0029-nav-student-prep-tabs.md) | 주 메뉴를 "학생 / 수업 준비"로 나누고, 수업 준비 결과는 브리핑부터 보여 준다 | Accepted (2026-10-21) |
| [0030](0030-local-pdf-open-via-ai-server.md) | 출처의 원본 PDF는 로컬 ai-server가 Chrome으로 그 쪽을 연다 — 등록부 pdfs.json + 인쇄 쪽→PDF 쪽 변환 | Accepted (2026-10-21) |
