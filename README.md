# 수업 노트 AI — 한국어 선생님을 위한 학생 학습관리 AI

1:1 온라인 한국어 선생님이 **학생이 떠나지 않게 하는 맞춤 수업과 성장 기록**을 꾸리도록 돕는 선생님 전용 웹 서비스. 학생별 수업 준비와 수업 후 정리를 AI 초안으로 만들고, 쌓인 기록으로 진도 리포트를 보여 준다.
요구사항은 [PRD.md](PRD.md), 설계 결정은 [docs/adr/](docs/adr/README.md), 기획 결정은 [docs/planning-adr/](docs/planning-adr/README.md).

```
학생 등록 → 수업 준비(15장 슬라이드 구성안 + 지침서 근거 브리핑) → 수업 → 수업 후 기록 → 프로필 갱신 ─┐
    ▲                                                                                  │
    └──────────────────────────────── 다음 수업 준비 ◀──────────────────────────────────┘
```

## 주요 기능
| 기능 | 내용 |
|---|---|
| 학생 등록 | 폼 입력, 또는 자연어 설명 → AI가 칸을 채운 초안 → 선생님이 확인 후 저장. **현재 수준(표준 등급 0~6)은 필수**, 학습 목적은 선생님이 고른다 (AI는 추천만, [기획 ADR-0018](docs/planning-adr/0018-level-from-trial-test-persona-by-teacher.md)) |
| 체험수업 레벨테스트 | 한글 읽기 + 1~6급 문법 질문·어휘를 국립국어원 표준 등급 목록에 묶어 제시, 맞음/틀림을 누르면 코드가 추천 등급을 계산. **학생 화면** 창을 따로 열어 화상수업에서 공유한다(문항만 보이고 예시 답·판정은 숨김). [결과 저장] → 선생님이 확인하면 새 학생 등록 또는 기존 학생 카드에 반영 ([기획 ADR-0021](docs/planning-adr/0021-student-screen-level-test-saved-result.md)) |
| 수업 준비 | **15장 슬라이드 구성안**(수업 목표·최종 미션 + 장마다 학생 화면 문구·교사 노트·숙제, [참고 문서](docs/reference/온라인_한국어_1대1_수업_PPT_제작_기준.md) 기준), **문화 포인트**(「세종한국문화」·지침서에서 찾은 후보 + 학생 나라 비교 질문), 복습/새 어휘/새 문법/숙제 구성안(코드 규칙), 개인화 설명·대본, **선생님 브리핑**(세종학당 교원용 지침서 근거의 문법 설명 포인트 + 출처 쪽수, 모국어 화자가 자주 틀리는 점, 예상 질문, 워밍업 질문, 맞춤 활용 활동), 범주별 승인·직접 수정·피드백. PPT는 만들지 않는다 ([기획 ADR-0015](docs/planning-adr/0015-no-ppt-fixed-lesson-frame.md), [기획 ADR-0032](docs/planning-adr/0032-slide-plan-from-reference.md)) |
| 수업 후 기록 | 짧은 메모 → 다룬 교재 항목, 잘한 점·틀린 점, 약점 추가·해결, 숙제, 학생에게 보낼 메시지(일본어·영어 + 한국어 번역) → **항목별 승인 후에만 반영** |
| 대시보드 | 할 일(미처리 기록, 승인 대기 수업안, 기록을 쓸 수업), 학생 카드, 시간 요약 |
| 학생 | 상단 [학생]. 학생 프로필 카드 목록(이름 검색, 상태·모국어·학습 목적 필터) → 카드를 누르면 학생 상세에서 프로필 보기·[정보 수정] |
| 커리큘럼·페르소나 | 상단 [커리큘럼·페르소나]. 탭 두 개: 온라인 세종학당 교육과정(입문 → 초급 1·2급 → 중급 3·4급 → 고급 5·6급, 특별 과정)을 표준 등급과 나란히 / 학습 목적 4가지의 대상·중심 교재·수업에서 강조할 점(참고)과 지금 그 목적에 속한 학생 |
| 어휘·문법 등급 목록 | 상단 [어휘·문법]. 국립국어원 표준 교육과정 문법 336개·어휘 10,635개를 등급·문법 분류·품사·검색어로 찾아보기(문법마다 이어진 교재 과 표시), 분류·품사 설명 탭 |
| 진도 리포트 | 학생별·기간별 새로 배운 문법·단어, 표준 등급별 배운 양, 해결한 약점, 반복 오류, 학생에게 보낼 메시지 초안(한국어 + 학생 언어). 숫자와 문장은 코드가 만든다 ([기획 ADR-0019](docs/planning-adr/0019-progress-report-for-retention.md)) |
| 채팅 | 조회("유이 요즘 약한 거 뭐야?"), 학생 등록, 수업 준비·기록 화면 연결, 한국어 교육 질문 |
| 지표 | **주 지표: AI 초안을 그대로 승인한 비율** (수업안 첫 검토 승인, 수업 후 기록 초안 유지 — [기획 ADR-0020](docs/planning-adr/0020-primary-metric-draft-quality.md)). 보조: 수업 준비·정리 시간 자동 기록(AI 대기 / 선생님 작업 분리), 기준 시간과 비교 |

원칙: **AI는 DB에 직접 쓰지 않는다.** 모든 쓰기는 선생님 승인을 거친다 (PRD 8-3, [ADR-0005](docs/adr/0005-data-access-ownership.md)).

## 구성
```
브라우저 ─▶ frontend :5173 ─▶ backend :8080 ─▶ ai-server :8000 ─▶ LLM (Ollama / Anthropic)
                                   │
                                   └─▶ Postgres :5432 (docker-compose)
```
브라우저는 backend만 호출하고, DB는 backend만 다룬다 ([ADR-0001](docs/adr/0001-service-role-split.md), [ADR-0006](docs/adr/0006-sse-proxy-path.md)).

### 폴더
```
.
├─ README.md, PRD.md, CLAUDE.md   실행 방법 / 요구사항 / Claude 작업 규칙
├─ docker-compose.yml             Postgres
├─ .env.example                   환경 변수 예시 (cp .env.example .env)
│
├─ frontend/        Vue 3 + Vite + TS + Pinia + PrimeVue + Tailwind
│  └─ src/
│     ├─ pages/         화면 (대시보드, 학생, 수업 준비·검토, 수업 기록, 레벨테스트, 리포트, 어휘·문법, 지표, 추적)
│     ├─ components/    화면 조각 (채팅 위젯, 브리핑 패널, 수업 틀, 학생 카드·폼 …)
│     ├─ api/           backend 호출 (http, SSE), 타입, mock/ (백엔드 없이 띄우는 가짜 응답)
│     └─ stores/        Pinia (채팅, 채팅 → 화면 넘기기)
│
├─ backend/         Spring Boot 4 + Spring AI 2 — API · DB · 채팅 라우터
│  └─ src/main/
│     ├─ java/com/koreantutor/
│     │  ├─ student/ lesson/ record/ leveltest/ report/   도메인별 API·DB
│     │  ├─ chat/        채팅 의도 분류(Spring AI)와 조회 답변
│     │  ├─ aiclient/    ai-server 호출, SSE 중계
│     │  └─ dashboard/ timelog/ material/ trace/ config/ common/
│     └─ resources/db/migration/   Flyway 스키마
│
├─ ai-server/       FastAPI + LangGraph — AI 작업 전부
│  ├─ app/
│  │  ├─ api/           엔드포인트 (prep, post_lesson, intake, grammar_qa, level_test, report, traces …)
│  │  ├─ agent/
│  │  │  ├─ lesson_prep/   수업 준비 그래프 (15장 슬라이드 구성안 + 브리핑, 승인에서 멈춤)
│  │  │  ├─ post_lesson/   수업 후 기록 추출 그래프
│  │  │  ├─ intake.py      자연어 → 학생 등록 초안
│  │  │  └─ grammar_qa.py  교재 근거 문법 질문
│  │  ├─ rag/           교재 PDF OCR → 청크 → bge-m3 색인, 원본 PDF 열기
│  │  ├─ standard/      표준 등급 목록, 레벨테스트 채점, 진도 리포트 계산, 모국어 노트
│  │  └─ persistence/   그래프 체크포인트
│  ├─ prompts/       LLM 프롬프트 (.md)
│  ├─ data/          표준 등급·교재 구성 JSON, 샘플 학생·녹취록, rag/ (색인, git 제외)
│  ├─ eval/          수업 후 기록 추출 정확도 평가
│  ├─ tests/         pytest
│  └─ cli.py         터미널에서 수업 준비 돌려 보기
│
├─ shared/constraints.json   세 서비스가 함께 쓰는 상수 (등급, 페르소나, 모국어, 채팅 의도 …)
├─ scripts/
│  ├─ dev.sh            전체 개발 서버 한 번에 띄우기
│  ├─ seed_demo.py      데모용 가상 학생 등록
│  └─ setup_ollama.sh   로컬 Ollama 모델 준비
│
└─ docs/
   ├─ planning-adr/     기획 결정 기록 (범위, 기능 우선순위, 지표 …)
   ├─ adr/              기술 설계 결정 기록 (구조, 라이브러리, API, 모델 …)
   ├─ troubleshooting/  막혔다가 푼 문제 기록
   └─ reference/        과제 안내서, 캡스톤 참고노트 (ADR 템플릿)
```
`ai-server/`의 수업 준비 그래프는 `korean-ppt-ai-agent` 저장소에서 옮겨 왔다.

## 준비물
- Docker, Java 21, Node 20+, [uv](https://docs.astral.sh/uv/)
- 로컬 [Ollama](https://ollama.com) `qwen3:8b` — 개발·데모·평가 모두 이걸로 한다 (API 비용 없음, [ADR-0020](docs/adr/0020-local-model-for-demo-too.md)). Anthropic API 키가 있으면 `.env`만 바꿔 쓸 수 있다
- Ollama `bge-m3` — 교수 자료 검색용 임베딩 (`ollama pull bge-m3`). 어떤 LLM을 쓰든 필요하다 ([ADR-0014](docs/adr/0014-teaching-material-rag.md))
- (선택) macOS — 교재 PDF OCR(Vision)을 직접 돌릴 때만

## 실행 ([ADR-0008](docs/adr/0008-local-dev-runtime.md), [ADR-0026](docs/adr/0026-single-dev-script.md))
```bash
cp .env.example .env              # ANTHROPIC_API_KEY 입력 (로컬 Ollama면 .env의 Ollama 블록 주석을 푼다)
bash scripts/setup_ollama.sh      # (Ollama를 쓸 때만) qwen3:8b 받기 + 메모리에 올리기

bash scripts/dev.sh               # Postgres + ai-server(:8000) + backend(:8080) + frontend(:5173) 한 번에
                                  # 저장하면 자동 반영, Ctrl+C로 전부 종료, 로그는 .dev-logs/ 에도 남는다
                                  # 채팅 화면만 만질 때: http://localhost:5173/?mock → 백엔드·RAG 없이 저장된 답으로 동작 (ADR-0027)

# (선택) 데모용 가상 학생 3명(사토 유이·히메나·Jay) 등록. 같은 이름이 있으면 프로필을 고치고, 다음 수업 일정도 하나 만든다
python3 scripts/seed_demo.py
docker exec -i tutor-postgres psql -U tutor -d tutor -v ON_ERROR_STOP=1 < scripts/seed_demo_history.sql   # 유이 1·2회차 기록, Jay 레벨테스트
```

### 교수 자료 색인 만들기 (한 번만, [ADR-0014](docs/adr/0014-teaching-material-rag.md))
세종학당재단 누리집에서 받은 PDF로 OCR → Parent-Child 청크 → 임베딩 색인을 만든다. 결과는 `ai-server/data/rag/`에 생기고 git에는 올리지 않는다.
색인이 없어도 서비스는 돌아가지만, 브리핑에 지침서 근거와 출처가 빠지고 문법 질문(채팅)에 교재 근거가 붙지 않는다.
```bash
cd ai-server
uv run python -m app.rag.ocr "<세종학당 한국어 1 교원용 지침서.pdf>" ko1_guide          # macOS, 292쪽 약 10분
uv run python -m app.rag.ocr "<실용 한국어 1 어휘와 문법 핸드북(영어).pdf>" practical1_handbook_en
uv run python -m app.rag.ocr "<세종학당 한국어 회화 어휘와 문법 1_일본어.pdf>" practical1_handbook_ja --ja   # 한국어·일본어 두 번 읽기, 약 1분
uv run python -m app.rag.ocr "<세종학당 한국어 회화 어휘와 문법 2_일본어.pdf>" practical2_handbook_ja --ja
uv run python -m app.rag.textlayer "<세종한국문화 1.pdf>" culture1 --layout            # 글자 층이 있는 PDF는 OCR 없이
uv run python -m app.rag.index                                                         # 약 1분
```
출처 옆 **"원문"** 버튼은 선생님 컴퓨터의 원본 PDF를 그 쪽으로 연다 (macOS + Chrome, [ADR-0030](docs/adr/0030-local-pdf-open-via-ai-server.md)). `ocr`·`textlayer`를 돌린 책은 PDF 위치가 자동으로 등록된다. 그 전에 색인한 책은 PDF 폴더를 한 번 스캔한다. 결과는 `ai-server/data/rag/pdfs.json`에 생긴다.
```bash
uv run python -m app.rag.pdfs scan ~/Desktop/한국어          # 쪽 수·파일명으로 책과 짝짓는다. 못 찾은 책을 알려 준다
uv run python -m app.rag.pdfs register ko1_guide "<pdf 경로>"   # 한 권만 직접 등록
```
처음 누르면 macOS가 "터미널이 Google Chrome을 제어하려고 합니다" 권한을 물을 수 있다. 허용해야 쪽 이동이 된다.
**나머지 자료 일괄 색인** ([기획 ADR-0028](docs/planning-adr/0028-index-all-materials.md), [ADR-0031](docs/adr/0031-catalog-batch-and-embed-cache.md)): `app/rag/catalog.json`의 책(본책·익힘책·비즈니스 등 111권)을 한 권씩 뽑는다. 전부 약 12시간. 끊겨도 같은 명령을 다시 실행하면 이어서 한다.
```bash
caffeinate -is uv run python -m app.rag.batch run ~/Desktop/한국어 --index   # 잠자기 막고 실행. 진행: data/rag/batch/batch.log
uv run python -m app.rag.batch status                                        # 책마다 done / running / failed / pending
```
`ollama serve`가 떠 있어야 마지막 색인 단계가 된다. 색인은 임베딩 캐시(`data/rag/embed_cache/`)를 써서 이미 임베딩한 조각은 다시 하지 않는다.

새 PDF를 넣으려면 `app/rag/chunk.py`의 `BOOKS`(형식을 맞춘 책)나 `catalog.json`(한 쪽 = 한 조각)에 한 줄 추가하고 같은 순서로 돌린다. `BOOKS`에는 기획 ADR-0025의 1순위 자료 24권이 있다 (지침서·매뉴얼·핸드북·문화 지침서). 글자 층이 있는 지침서(입문, 5A~6B)는 `textlayer`로, 나머지는 `ocr`로 뽑는다.
문법 질문은 청크에 붙은 형태 키 태그(teaches/mentions)로 근거를 찾는다. 새 책은 `BOOKS`에 `kind`와 `teaches` 규칙을 적는다. 형식을 모르는 책은 `layout: "ocr_page"`(또는 `"text_page"`)로 한 쪽씩 넣으면 mentions만 붙는다. 같은 시리즈 핸드북의 영어판·일본어판은 색인에서 한 덩어리로 합쳐진다 ([ADR-0025](docs/adr/0025-form-key-tags-and-merged-editions.md)).

### 단원 시트 만들기 ([기획 ADR-0030](docs/planning-adr/0030-unit-sheets-from-materials.md), [ADR-0032](docs/adr/0032-unit-sheets-and-standard-ids.md))
수업 준비는 교재·과마다 "가르칠 문법·어휘·예문" 시트를 읽는다 (`ai-server/data/curriculum/<교재>/unit_NN.json`, git 밖). 지침서 색인이 있어야 만들 수 있다.
```bash
cd ai-server
uv run python -m app.curriculum.build ko1            # 「세종학당 한국어 1」 20과 초안 (status: draft). 검수된 시트는 덮어쓰지 않는다
uv run python -m app.curriculum.build ko2
uv run python -m app.curriculum.convert_textbook      # 손으로 만든 data/textbook/ 2~4과 → 검수된 시트 (status: reviewed)
uv run python -m app.curriculum.evaluate ko1          # 초안을 2~4과 정답과 비교 (정밀도·재현율)
```
선생님이 확인한 시트는 파일의 `"status"`를 `"reviewed"`로 바꾼다 (검수 화면은 아직 없음).

### 표준 등급 목록 ([기획 ADR-0016](docs/planning-adr/0016-persona-anchor-textbook-standard-levels.md), [ADR-0016](docs/adr/0016-standard-level-list-and-item-ids.md))
국립국어원 「국제 통용 한국어 표준 교육과정 적용 연구(4단계)」(2017)의 어휘·문법 등급 목록(1~6급, 문법 336개, 어휘 10,635개)을 학생 수준·예문 수준의 공통 기준으로 쓴다.
공공누리 제1유형(출처표시)이라 저장소에 들어 있다 (`ai-server/data/standard/`). 따로 할 일은 없다. 원본 엑셀이 바뀌었을 때만 다시 가져온다.
```bash
cd ai-server
uv run python -m app.standard.importer          # data/standard/source/*.xlsx → grammar.json, vocab.json
uv run python -c "from app.standard.levels import sentence_level; print(sentence_level('한국 드라마를 좋아합니다.'))"
```
교재 문법 → 표준 항목 대응표는 `ai-server/data/standard/textbook_map.json`이다 (지금은 「한국어 1」 2~4과).
체험수업 레벨테스트 문항은 `ai-server/data/standard/level_test.json`이다. 문항마다 표준 항목 ID가 붙어 있고, 서버가 뜰 때 ID와 등급이 맞는지 검사한다.

## 데모 시나리오 (PRD 5장)
0. **레벨테스트** — 상단 [더보기] → [레벨테스트] → [학생 화면 열기]로 뜬 창을 옆에 둔다 → 한글 단어를 누르면 학생 창에 크게 뜨는지 확인 → 한글 5개, 1급 문항을 맞음으로, 2급 문항 몇 개를 틀림으로 누른다(누를 때마다 학생 창이 다음 문항으로) → 오른쪽 추천이 "표준 2급"으로 바뀌는지 확인 → [결과 저장] → 학생 창이 "수고했어요"로 바뀜 → 결과 카드에서 [새 학생으로 등록]
1. **S1 학생 등록** — (레벨테스트에서 넘어왔거나) [학생 등록] → 왼쪽에 "일본인 대학생 유이, 한글은 읽음, 드라마 좋아하고 내년에 서울 여행 가고 싶대. 받침 발음이 약함" → [초안 만들기] → 칸 확인 → 저장
2. **S2 수업 준비** — 상단 [수업 준비] → 일정 순 학생 카드에서 유이의 [수업 준비] (학생 화면 [다음 수업 준비]도 같음) → 진행 단계 표시 → 학생 요약 줄·브리핑(지침서 출처)·15장 구성안·4개 범주 확인 → 한 범주에 피드백 → 다시 만든 범주 승인 → [글로 복사]로 수업안을 자기 자료에 붙여 넣기. 유이(ja, 1급·여행)와 Jay(en, 입문·회화)를 준비해 브리핑 차이를 비교한다
3. **S3 수업 후 기록** — [수업 후 기록] → "3과 1~10 단어 함. -습니다 잘함. 을/를 받침 구분 계속 틀림. 숙제는 연습문제 2번" → [AI로 정리하기] → 항목 체크 (녹취록으로 해 보려면 [녹취록 파일 불러오기 (.txt)]로 `ai-server/data/samples/transcript_sample_ja.txt`) → 메시지 복사 → [승인하고 반영] → 학생 화면에서 약점 변화 확인
4. **S4 채팅** — "유이 요즘 약한 거 뭐야?" / "유이 다음 수업 40분으로 준비해줘" → [수업 준비 화면 열기]
5. **진도 리포트** — 학생 화면 [진도 리포트] → 기간 [전체] → 새로 배운 것·해결한 약점 확인 → 학생 언어 메시지를 고쳐 [복사]
6. **지표** — [더보기] → [지표]에서 수업안 첫 검토 승인 비율·수업 후 기록 초안 유지 비율(주 지표) 확인 → 아래 시간(보조)에 기준 시간 입력 → 감소율 확인

수업 준비는 로컬 모델이라 몇 분 걸린다. 데모 영상에서는 미리 준비해 둔 수업을 함께 보여 주면 좋다.

### API로 수업 준비 해 보기 (화면 없이)
```bash
curl -X POST localhost:8080/api/students -H 'Content-Type: application/json' \
  -d '{"name":"사토 유이","nativeLanguage":"ja","nextUnit":3,"weaknesses":[{"description":"받침 발음"}]}'
curl -X POST localhost:8080/api/students/1/lessons -H 'Content-Type: application/json' -d '{}'
curl -N -X POST localhost:8080/api/lessons/1/prep            # SSE … review_required 에서 멈춤
curl -N -X POST localhost:8080/api/lessons/1/prep/review -H 'Content-Type: application/json' \
  -d '{"decisions":{"review":{"action":"approve"},"new_vocab":{"action":"approve"},"new_grammar":{"action":"approve"},"homework":{"action":"approve"}}}'
curl localhost:8080/api/lessons/1                            # briefing.slide_plan 에 15장 슬라이드 구성안
```

## 테스트와 평가
```bash
cd ai-server && uv run pytest     # 가짜 LLM으로 그래프 분기·권위 게이트·API·채점 규칙 (LLM 호출 없음)
cd backend && ./gradlew test      # Testcontainers Postgres + 가짜 ai-server (Docker 필요)
cd frontend && npm run typecheck  # 타입 검사

# 수업 후 기록 추출 정확도 (PRD 10장, 목표 0.8) — 실제 LLM 호출
cd ai-server && uv run python -m eval.run_eval
```
평가 데이터셋은 [ai-server/eval/dataset.json](ai-server/eval/dataset.json) (가상 메모 16개, 함정 케이스 포함). 결과는 `ai-server/eval/results/`에 표(.md)와 원자료(.json)로 남는다.

### LLM 실행 추적 (LangSmith, [ADR-0028](docs/adr/0028-langsmith-tracing-and-trace-page.md))
`.env`에 `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`를 넣고 `bash scripts/dev.sh`를 다시 실행하면 ai-server의 그래프·LLM 호출·RAG 검색·코드 점검이 LangSmith에 기록된다.
앱 상단의 **AI 추적** 탭에서 최근 실행 목록과, 실행 하나의 흐름(노드 → 함수 → LLM 호출, 시간 막대)을 볼 수 있다. Spring AI 채팅 라우터는 아직 기록하지 않는다.

## 알려진 한계
- 단일 선생님용 로컬 서비스다. 로그인·권한이 없다 (PRD 비목표).
- 수업 구성(진도·학습 항목 ID)은 세종학당 한국어 1권 2~4과 JSON뿐이다. 지침서·핸드북은 검색 색인으로만 쓴다. 페르소나별 중심 교재(기획 ADR-0016)는 결정만 했고, 다른 교재의 과별 데이터와 학생 페르소나 칸은 아직 없다.
- 예문을 자료에서 찾고 등급으로 거르는 방식(기획 ADR-0017)은 등급 판정 함수까지만 있다. 수업 준비의 설명 노드는 아직 LLM이 예문을 만든다.
- 예문 등급은 어휘만 본다. 문장 안 문법 표현의 등급은 보지 않는다.
- 진도 리포트의 학생 언어 메시지 안에서 잘한 점·극복한 것은 수업 기록의 한국어 그대로 나온다. 보내기 전에 고쳐야 한다. 등급별 숫자는 「한국어 1」 2~4과 대응표 범위만 반영한다.
- 레벨테스트 문항(질문·예시 답)은 Claude 초안이고 선생님 검수 전이다. 문항별 결과는 저장하지만 아직 다시 볼 화면은 결과 카드뿐이다(학생별 이력 화면 없음).
- 레벨테스트 학생 화면은 선생님 화면과 같은 브라우저에서 연 창이어야 따라온다. 학생이 다른 기기에서 직접 들어올 수는 없다.
- 표준 등급 칸을 넣기 전에 등록한 학생은 수준이 "수준 미정"이다. 정보를 고칠 때 등급을 골라야 저장된다.
- 모국어별 실수·예상 질문은 `ai-server/data/standard/l1_notes.json`(2~4과 문법 7개 × 일본어·영어)에서 꺼낸다. 아직 모두 Claude 초안(`reviewed: false`)이라 화면에 "검수 전"으로 표시한다. 검수하면 파일에서 `reviewed`를 `true`로 바꾼다. 데이터에 없는 문법은 LLM이 만들고 "검수 필요"로 표시한다 ([ADR-0022](docs/adr/0022-l1-notes-data.md)).
- 채팅 대화 기록은 backend 메모리에만 있어서 재시작하면 사라진다.
- 수업 준비 도중 화면을 떠나면 실행이 멈춘다. 다시 들어오면 [다시 시작]으로 처음부터 만든다.
- 교재 데이터(`ai-server/data/textbook/`), 교재 PDF, OCR 결과·색인(`ai-server/data/rag/`)은 저작권 때문에 git에 올리지 않는다.

## 기타
- 수업 준비 그래프만 터미널에서 돌려 보기: `cd ai-server && uv run python cli.py --lang ja`
